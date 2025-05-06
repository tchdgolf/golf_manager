# app/routes/admin/views_ticket_template.py
from flask import render_template, redirect, url_for, flash, request
from . import bp # admin 블루프린트
from app.extensions import db
from app.models import TicketTemplate # TicketTemplate 모델
from app.models.ticket_template import TicketCategory # Enum
from app.forms.admin_forms import TicketTemplateForm # 폼

# 이용권 템플릿 목록
@bp.route('/ticket_templates')
def list_ticket_templates():
    page = request.args.get('page', 1, type=int)
    # 활성/비활성 필터 (선택적)
    show_inactive = request.args.get('show_inactive', type=bool, default=False)
    query = TicketTemplate.query
    if not show_inactive:
        query = query.filter_by(is_active=True)

    pagination = query.order_by(TicketTemplate.category, TicketTemplate.name).paginate(page=page, per_page=10, error_out=False)
    templates = pagination.items
    return render_template('ticket_template/list_templates.html',
                           templates=templates, pagination=pagination,
                           title="이용권 템플릿 목록", show_inactive=show_inactive)

# 이용권 템플릿 추가
@bp.route('/ticket_templates/add', methods=['GET', 'POST'])
def add_ticket_template():
    form = TicketTemplateForm()
    if form.validate_on_submit():
        template = TicketTemplate(
            name=form.name.data,
            category=form.category.data,
            duration_days=form.duration_days.data,
            total_count=form.total_count.data,
            total_lesson_count=form.total_lesson_count.data,
            default_validity_days=form.default_validity_days.data,
            price=form.price.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        db.session.add(template)
        try:
            db.session.commit()
            flash(f'이용권 템플릿 "{template.name}"이(가) 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('admin.list_ticket_templates'))
        except Exception as e:
            db.session.rollback()
            flash(f'템플릿 추가 중 오류 발생: {e}', 'danger')
    return render_template('ticket_template/template_form.html', form=form, title="이용권 템플릿 추가",
                           TicketCategory=TicketCategory)

# 이용권 템플릿 수정
@bp.route('/ticket_templates/edit/<int:template_id>', methods=['GET', 'POST'])
def edit_ticket_template(template_id):
    template = db.session.get(TicketTemplate, template_id)
    if not template:
        flash('해당 템플릿을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_ticket_templates'))

    form = TicketTemplateForm(obj=template, original_name=template.name) # obj=template 으로 폼 필드 자동 채움

    if form.validate_on_submit():
        form.populate_obj(template) # 폼 데이터를 template 객체에 반영
        try:
            db.session.commit()
            flash(f'이용권 템플릿 "{template.name}"의 정보가 수정되었습니다.', 'success')
            return redirect(url_for('admin.list_ticket_templates'))
        except Exception as e:
            db.session.rollback()
            flash(f'템플릿 수정 중 오류 발생: {e}', 'danger')
    # GET 요청 시에는 obj=template 으로 이미 필드가 채워짐
    # (또는 수동으로: elif request.method == 'GET': form.process(obj=template) )

    return render_template('ticket_template/template_form.html',
                           form=form, title="이용권 템플릿 수정", template=template,
                           TicketCategory=TicketCategory) # TicketCategory 전달

# 이용권 템플릿 활성/비활성 토글 (논리적 삭제 대신)
@bp.route('/ticket_templates/toggle_active/<int:template_id>', methods=['POST'])
def toggle_active_ticket_template(template_id):
    template = db.session.get(TicketTemplate, template_id)
    if not template:
        flash('해당 템플릿을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_ticket_templates'))

    template.is_active = not template.is_active
    try:
        db.session.commit()
        status = "활성화" if template.is_active else "비활성화"
        flash(f'이용권 템플릿 "{template.name}"이(가) {status}되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'템플릿 상태 변경 중 오류 발생: {e}', 'danger')
    return redirect(url_for('admin.list_ticket_templates', show_inactive=True)) # 변경 후 모든 목록 보여주기