# app/routes/admin/views_ticket.py
import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from . import bp # admin 블루프린트
from app.extensions import db
from app.models import User, Pro, TicketTemplate, Ticket # 필요한 모델들
from app.forms.admin_forms import TicketIssueForm
from app.models.ticket_template import TicketCategory 
# from app.services import ticket_service, user_service # 나중에 서비스 로직 임포트

# 이용권 발급 페이지
@bp.route('/tickets/issue', methods=['GET', 'POST'])
@bp.route('/tickets/issue/user/<int:user_id_from_url>', methods=['GET', 'POST']) # 회원 상세에서 넘어올 경우
def issue_ticket(user_id_from_url=None):
    form = TicketIssueForm()

    # SelectField choices 동적 로딩
    # 모든 사용자 목록 (탈퇴 회원 등 제외 로직 추가 가능)
    form.user_id.choices = [(u.id, f"{u.name} ({u.phone})") for u in User.query.order_by(User.name).all()]
    # 활성화된 이용권 템플릿 목록 (카테고리별 정렬 등 가능)
    form.ticket_template_id.choices = [('', '템플릿 선택 안 함')] + \
                                      [(t.id, f"{t.name} ({t.category.value})") for t in TicketTemplate.query.filter_by(is_active=True).order_by(TicketTemplate.name).all()]
    # 모든 프로 목록
    form.pro_id.choices = [('', '담당 프로 없음')] + \
                          [(p.id, p.name) for p in Pro.query.order_by(Pro.name).all()]

    # URL을 통해 특정 회원이 미리 선택된 경우
    if user_id_from_url and request.method == 'GET':
        form.user_id.data = user_id_from_url

    # 선택된 회원의 현재 이용권 목록 (Ajax 로드 또는 초기 로드)
    current_tickets = []
    selected_user_id = form.user_id.data or user_id_from_url
    if selected_user_id:
        # selected_user = db.session.get(User, selected_user_id)
        # if selected_user:
        #     current_tickets = selected_user.tickets.order_by(Ticket.expiry_date.desc()).all()
        # 위 코드는 나중에 User 모델에 tickets 관계 설정 후 사용
        # 지금은 임시로 빈 리스트
        pass


    if form.validate_on_submit():
        # --- ▼ 이용권 발급 로직 (나중에 ticket_service로 분리) ▼ ---
        try:
            # 1. 사용자 가져오기
            user = db.session.get(User, form.user_id.data)
            if not user:
                flash('선택된 회원을 찾을 수 없습니다.', 'danger')
                # 폼을 다시 렌더링하며 오류 유지
                return render_template('ticket/issue_ticket_form.html', title="이용권 발급", form=form, current_tickets=current_tickets)

            # 2. 템플릿 정보 가져오기 (선택 사항)
            template = None
            if form.ticket_template_id.data:
                template = db.session.get(TicketTemplate, form.ticket_template_id.data)

            # 3. 티켓 정보 설정 (템플릿 우선, 없으면 수동 입력값 사용)
            ticket_name = form.name.data
            start_date = form.start_date.data
            pro_id = form.pro_id.data or None # 빈 문자열이면 None으로
            price = form.price.data
            memo = form.memo.data

            # 템플릿이 있으면 템플릿 정보 우선 사용
            if template:
                if not ticket_name: # 이름 입력 안했으면 템플릿 기반 자동 생성
                    ticket_name = template.generate_ticket_name() # User 정보도 넘겨서 개인화 가능
                # 가격도 템플릿 우선
                if price is None and template.price is not None:
                    price = template.price

                # 카테고리에 따라 횟수, 기간, 만료일 등 설정
                category = template.category
                total_taseok = template.total_count
                total_lesson = template.total_lesson_count
                duration_days = template.duration_days
                validity_days_from_template = template.default_validity_days # 횟수제 템플릿의 유효기간

                if category in [TicketCategory.PERIOD, TicketCategory.COMBO] and duration_days:
                    expiry_date = start_date + datetime.timedelta(days=duration_days -1) # 시작일 포함
                elif category in [TicketCategory.COUNT, TicketCategory.COUPON] and validity_days_from_template:
                    expiry_date = start_date + datetime.timedelta(days=validity_days_from_template -1)
                else: # LESSON_ADD 또는 유효기간 없는 경우
                    expiry_date = None
            else: # 템플릿 미사용 (수동 입력)
                # 수동 입력 값으로 횟수, 기간, 만료일 설정
                total_taseok = form.total_taseok_count_manual.data
                total_lesson = form.total_lesson_count_manual.data
                duration_days_m = form.duration_days_manual.data
                validity_days_m = form.validity_days_manual.data

                if duration_days_m: # 기간 우선
                    expiry_date = start_date + datetime.timedelta(days=duration_days_m -1)
                elif validity_days_m: # 그 다음 횟수제 유효기간
                    expiry_date = start_date + datetime.timedelta(days=validity_days_m -1)
                else:
                    expiry_date = None # 만료일 없는 횟수권 (예: 레슨 추가)

            # 4. Ticket 객체 생성
            new_ticket = Ticket(
                user_id=user.id,
                ticket_template_id=template.id if template else None,
                name=ticket_name,
                start_date=start_date,
                expiry_date=expiry_date,
                total_taseok_count=total_taseok,
                remaining_taseok_count=total_taseok, # 초기에는 총 횟수와 동일
                total_lesson_count=total_lesson,
                remaining_lesson_count=total_lesson, # 초기에는 총 횟수와 동일
                pro_id=pro_id,
                price=price,
                memo=memo
            )
            new_ticket.update_status() # 초기 상태 업데이트
            db.session.add(new_ticket)

            # 5. User 모델 업데이트 (레슨 횟수, 최종 만료일) - user_service 사용 권장
            if total_lesson:
                user.remaining_lesson_total = (user.remaining_lesson_total or 0) + total_lesson
            if expiry_date:
                if user.master_expiry_date is None or expiry_date > user.master_expiry_date:
                    user.master_expiry_date = expiry_date
            # user_service.recalculate_master_expiry_date(user) # 나중에 이렇게 변경

            db.session.commit()
            flash(f'회원 "{user.name}"님께 이용권 "{new_ticket.name}"이(가) 성공적으로 발급되었습니다.', 'success')
            return redirect(url_for('admin.view_user', user_id=user.id)) # 발급 후 회원 상세 페이지로

        except Exception as e:
            db.session.rollback()
            flash(f'이용권 발급 중 오류가 발생했습니다: {e}', 'danger')
        # --- ▲ 이용권 발급 로직 끝 ▲ ---

    return render_template('ticket/issue_ticket_form.html', title="이용권 발급", form=form, current_tickets=current_tickets)


# (선택적) 템플릿 선택 시 템플릿 정보 가져오는 API (JavaScript에서 사용)
@bp.route('/api/ticket_template/<int:template_id>')
def get_ticket_template_info(template_id):
    template = db.session.get(TicketTemplate, template_id)
    if template:
        return jsonify({
            'name': template.generate_ticket_name(), # User 정보 없이 기본 이름 생성
            'category': template.category.name, # Enum의 name
            'category_value': template.category.value, # Enum의 value
            'duration_days': template.duration_days,
            'total_count': template.total_count,
            'total_lesson_count': template.total_lesson_count,
            'default_validity_days': template.default_validity_days,
            'price': template.price
        })
    return jsonify({'error': 'Template not found'}), 404


# --- ▼ 회원 정보 및 보유 티켓 목록 API 추가 ▼ ---
@bp.route('/api/user/<int:user_id>/tickets')
def get_user_tickets_info(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    tickets_data = []
    # User 모델에 tickets 관계가 설정되어 있어야 함 (이전에 Ticket 모델에 user 관계 설정함)
    # 활성화된 티켓, 만료일 순 정렬 등 필요에 따라 쿼리 수정
    user_tickets = user.tickets.order_by(Ticket.expiry_date.desc(), Ticket.created_at.desc()).all()

    for ticket in user_tickets:
        tickets_data.append({
            'id': ticket.id,
            'name': ticket.name,
            'start_date': ticket.start_date.isoformat() if ticket.start_date else None,
            'expiry_date': ticket.expiry_date.isoformat() if ticket.expiry_date else None,
            'total_taseok_count': ticket.total_taseok_count,
            'remaining_taseok_count': ticket.remaining_taseok_count,
            'total_lesson_count': ticket.total_lesson_count,
            'remaining_lesson_count': ticket.remaining_lesson_count,
            'is_active': ticket.is_active,
            'is_used_up': ticket.is_used_up,
            'is_expired': ticket.is_expired
            # 필요시 pro 정보 등 추가
        })

    return jsonify({
        'user_id': user.id,
        'name': user.name,
        'phone': user.phone,
        'master_expiry_date': user.master_expiry_date.isoformat() if user.master_expiry_date else None,
        'remaining_lesson_total': user.remaining_lesson_total,
        'tickets': tickets_data
    })

@bp.route('/tickets/edit/<int:ticket_id>', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        flash('해당 이용권을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_users')) # 또는 다른 적절한 페이지

    # 수정 전 레슨 횟수 기록 (User 모델 연동용)
    original_remaining_lesson = ticket.remaining_lesson_count or 0

    form = TicketEditForm(obj=ticket) # 폼 로드 시 현재 티켓 정보 채우기

    if form.validate_on_submit():
        # 폼 데이터로 티켓 객체 업데이트 (주의: obj=ticket으로 초기화했으므로, 필드별로 할당하는 것이 더 안전할 수 있음)
        # form.populate_obj(ticket) # 이 방식 대신 필드별 할당 권장

        ticket.name = form.name.data
        # 시작일, 만료일, 총 횟수 등 수정 로직은 정책 확정 후 추가

        # 잔여 횟수 업데이트
        ticket.remaining_taseok_count = form.remaining_taseok_count.data
        new_remaining_lesson = form.remaining_lesson_count.data or 0
        ticket.remaining_lesson_count = new_remaining_lesson

        ticket.pro_id = form.pro_id.data # coerce 함수 덕분에 int 또는 None
        ticket.price = form.price.data
        ticket.memo = form.memo.data
        ticket.is_active = form.is_active.data # 관리자가 직접 활성 상태 변경

        # 상태 재계산 (만료/소진 여부 등)
        ticket.update_status()

        # --- User 모델 연동 로직 (나중에 user_service로 분리) ---
        try:
            # 1. 레슨 횟수 변동분 계산 및 User.remaining_lesson_total 업데이트
            lesson_diff = new_remaining_lesson - original_remaining_lesson
            user = ticket.user # 티켓 소유자
            if user:
                user.remaining_lesson_total = (user.remaining_lesson_total or 0) + lesson_diff
            else:
                # 이론적으로는 발생하기 어려움
                flash("티켓 소유자 정보를 찾을 수 없어 레슨 횟수 연동에 실패했습니다.", "error")

            # 2. 최종 만료일 재계산 (ticket.update_status() 호출만으로도 될 수 있으나, 명시적 호출 권장)
            # user_service.recalculate_master_expiry_date(user) # 서비스 구현 후 사용

            db.session.commit()
            flash(f'이용권 정보 (ID: {ticket.id})가 수정되었습니다.', 'success')
            return redirect(url_for('admin.view_user', user_id=ticket.user_id)) # 회원 상세 페이지로

        except Exception as e:
            db.session.rollback()
            flash(f'이용권 수정 중 오류가 발생했습니다: {e}', 'danger')

    elif request.method == 'GET':
         # GET 요청 시 pro_id 선택지가 form.__init__에서 로드됨
         pass # obj=ticket으로 이미 폼 데이터 채워짐

    return render_template('ticket/edit_ticket_form.html', form=form, title="이용권 정보 수정", ticket=ticket)

# 이용권 삭제 (기본 틀)
@bp.route('/tickets/delete/<int:ticket_id>', methods=['POST'])
def delete_ticket(ticket_id):
    # ... (이전 기본 틀 유지 - 나중에 구현) ...
     ticket = db.session.get(Ticket, ticket_id) # 임시 추가 (리디렉션용)
     if not ticket: ticket_user_id = None
     else: ticket_user_id = ticket.user_id
     flash(f'이용권 삭제 기능 (ID: {ticket_id}) 은 아직 구현되지 않았습니다.', 'info')
     if ticket_user_id: return redirect(url_for('admin.view_user', user_id=ticket_user_id))
     else: return redirect(url_for('admin.list_users')) # 임시