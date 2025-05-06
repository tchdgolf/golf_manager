# app/forms/admin_forms.py
from wtforms import StringField, SubmitField, SelectField, BooleanField, TextAreaField, PasswordField, IntegerField, DateField, DateTimeLocalField
from flask_wtf import FlaskForm
from wtforms.widgets import DateInput, DateTimeLocalInput
from wtforms.validators import DataRequired, Length, ValidationError, Email, Optional, NumberRange
from app.models import Pro, Booth, User, TicketTemplate, Ticket, Holding
from app.models.enums import BoothSystemType, BookingType # Enum 임포트
from app.models.ticket_template import TicketCategory 


def coerce_int_or_none(value):
    if value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


class BoothForm(FlaskForm):
    """타석(부스) 등록/수정 폼"""
    name = StringField('타석 이름', validators=[
        DataRequired(message="타석 이름을 입력해주세요."),
        Length(min=2, max=100, message="이름은 2자 이상 100자 이하로 입력해주세요.")
    ])
    # Enum을 사용하는 SelectField: choices는 (value, label) 튜플 리스트
    system_type = SelectField('시스템 종류', coerce=BoothSystemType, validators=[DataRequired()],
                              # choices=[(choice, choice.value) for choice in BoothSystemType]) # 기존
                              choices=[(choice.value, choice.value) for choice in BoothSystemType]) # 수정: (Enum값문자열, 보여줄텍스트)
    is_available = BooleanField('예약 가능 상태', default=True) # 체크박스
    memo = TextAreaField('메모 (선택 사항)')
    submit = SubmitField('저장')

    # 이름 중복 검증 (수정 시 자기 자신은 제외)
    def __init__(self, original_name=None, *args, **kwargs):
        super(BoothForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if self.original_name and self.original_name == name.data:
            return
        booth = Booth.query.filter_by(name=name.data).first()
        if booth:
            raise ValidationError('이미 등록된 타석 이름입니다.')

class ProForm(FlaskForm):
    """프로(강사) 등록/수정 폼"""
    name = StringField('프로 이름', validators=[
        DataRequired(message="프로 이름을 입력해주세요."),
        Length(min=2, max=100, message="이름은 2자 이상 100자 이하로 입력해주세요.")
    ])
    submit = SubmitField('저장')

    # 이름 중복 검증 (수정 시 자기 자신은 제외)
    def __init__(self, original_name=None, *args, **kwargs):
        super(ProForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        # 수정 모드이고 이름이 변경되지 않았다면 중복 검사 패스
        if self.original_name and self.original_name == name.data:
            return
        # 다른 프로와 이름이 중복되는지 검사
        pro = Pro.query.filter_by(name=name.data).first()
        if pro:
            raise ValidationError('이미 등록된 프로 이름입니다.')


class UserEditForm(FlaskForm):
    """회원 정보 수정 폼 (관리자용)"""
    name = StringField('이름', validators=[DataRequired(), Length(min=2, max=100)])
    # phone 필드는 고유 식별자이므로 여기서 수정하지 않음 (필요시 별도 기능)
    memo = TextAreaField('메모')
    is_admin = BooleanField('관리자 권한 부여')
    submit = SubmitField('정보 수정')

    # 관리자 권한 변경 시 자기 자신을 일반 사용자로 변경하는 것을 막는 로직 (선택적)
    def __init__(self, current_user_id=None, editing_user_id=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.current_user_id = current_user_id
        self.editing_user_id = editing_user_id

    def validate_is_admin(self, is_admin_field):
        # 현재 로그인한 관리자가 자기 자신의 관리자 권한을 해제하려고 할 때
        if self.current_user_id == self.editing_user_id and not is_admin_field.data:
            # 마지막 관리자인지 확인 (선택적 심화 로직)
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                raise ValidationError('마지막 관리자의 권한은 해제할 수 없습니다. 다른 관리자를 먼저 지정해주세요.')
            # raise ValidationError('자기 자신의 관리자 권한은 여기서 해제할 수 없습니다.')


class UserPasswordResetForm(FlaskForm):
    """회원 비밀번호 초기화 폼 (관리자용)"""
    submit = SubmitField('비밀번호를 \'0000\'으로 초기화')



class TicketTemplateForm(FlaskForm):
    """이용권 템플릿 등록/수정 폼"""
    name = StringField('템플릿 이름', validators=[
        DataRequired(message="템플릿 이름을 입력해주세요."),
        Length(min=2, max=100)
    ])
    category = SelectField('이용권 대분류', coerce=TicketCategory, validators=[DataRequired()],
                           choices=[(cat.value, cat.value) for cat in TicketCategory]) # 수정: (Enum값문자열, 보여줄텍스트)

    # 기간 관련 필드 (기간권, 종합권)
    duration_days = IntegerField('유효 기간 (일 수)', validators=[Optional(), NumberRange(min=1)],
                                 description="예: 1개월은 30, 3개월은 90으로 입력. 기간제 상품에만 해당.")

    # 횟수 관련 필드 (횟수권, 쿠폰, 레슨추가, 종합권)
    total_count = IntegerField('총 타석 이용 횟수', validators=[Optional(), NumberRange(min=1)],
                               description="타석 이용이 포함된 횟수제 상품에만 해당.")
    total_lesson_count = IntegerField('총 레슨 횟수', validators=[Optional(), NumberRange(min=1)],
                                     description="레슨이 포함된 상품에만 해당.")

    # 횟수제 상품의 기본 유효기간
    default_validity_days = IntegerField('횟수제 기본 유효기간 (일 수)', validators=[Optional(), NumberRange(min=1)],
                                         description="횟수권/쿠폰/레슨추가 상품의 기본 유효 기간 (예: 10회권 60일).")

    price = IntegerField('기본 판매 가격 (원)', validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField('설명 (선택 사항)')
    is_active = BooleanField('활성 상태 (판매 가능)', default=True)
    submit = SubmitField('저장')

    # 이름 중복 검증
    def __init__(self, original_name=None, *args, **kwargs):
        super(TicketTemplateForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if self.original_name and self.original_name == name.data:
            return
        template = TicketTemplate.query.filter_by(name=name.data).first()
        if template:
            raise ValidationError('이미 등록된 템플릿 이름입니다.')

    # 카테고리별 필드 유효성 검사 (선택적 추가 가능)
    def validate(self, extra_validators=None):
        # 기본 WTForms 유효성 검사 먼저 실행
        if not super(TicketTemplateForm, self).validate(extra_validators):
            return False

        # 카테고리별 필수 필드 검사
        category = self.category.data
        is_valid = True

        if category == TicketCategory.PERIOD:
            if not self.duration_days.data:
                self.duration_days.errors.append('기간권은 유효 기간(일 수)이 필수입니다.')
                is_valid = False
        elif category == TicketCategory.COUNT:
            if not self.total_count.data:
                self.total_count.errors.append('횟수권은 총 타석 이용 횟수가 필수입니다.')
                is_valid = False
            if not self.default_validity_days.data: # 횟수권의 유효기간
                self.default_validity_days.errors.append('횟수권은 기본 유효기간(일 수)이 필수입니다.')
                is_valid = False
        elif category == TicketCategory.COUPON:
            if not self.total_count.data or not self.total_lesson_count.data:
                self.total_count.errors.append('쿠폰 레슨은 총 타석 및 레슨 횟수가 필수입니다.')
                self.total_lesson_count.errors.append('쿠폰 레슨은 총 타석 및 레슨 횟수가 필수입니다.')
                is_valid = False
            if self.total_count.data != self.total_lesson_count.data:
                self.total_count.errors.append('쿠폰 레슨은 타석 횟수와 레슨 횟수가 동일해야 합니다.')
                self.total_lesson_count.errors.append('쿠폰 레슨은 타석 횟수와 레슨 횟수가 동일해야 합니다.')
                is_valid = False
            if not self.default_validity_days.data: # 쿠폰의 유효기간
                self.default_validity_days.errors.append('쿠폰 레슨은 기본 유효기간(일 수)이 필수입니다.')
                is_valid = False
        elif category == TicketCategory.LESSON_ADD:
            if not self.total_lesson_count.data:
                self.total_lesson_count.errors.append('레슨 추가는 총 레슨 횟수가 필수입니다.')
                is_valid = False
            # 레슨 추가는 유효기간 없음 (default_validity_days 불필요)
        elif category == TicketCategory.COMBO:
            if not self.duration_days.data:
                self.duration_days.errors.append('종합권은 유효 기간(일 수)이 필수입니다.')
                is_valid = False
            if not self.total_lesson_count.data: # 종합권은 레슨 횟수가 필수라고 가정
                self.total_lesson_count.errors.append('종합권은 총 레슨 횟수가 필수입니다.')
                is_valid = False
        return is_valid
    

class TicketIssueForm(FlaskForm):
    """이용권 발급 폼"""
    user_id = SelectField('회원 선택', coerce=int, validators=[DataRequired(message="회원을 선택해주세요.")])
    # user_id의 choices는 라우트에서 동적으로 채워줍니다.

    ticket_template_id = SelectField('템플릿 선택 (선택 사항)', coerce=coerce_int_or_none, validators=[Optional()])
    # ticket_template_id의 choices도 라우트에서 동적으로 채워줍니다.

    # --- 템플릿 미사용 시 또는 템플릿 정보 오버라이드 시 직접 입력할 필드들 ---
    # (템플릿 선택 시 이 필드들은 자동으로 채워지거나 비활성화될 수 있음 - JavaScript로 처리)
    name = StringField('이용권 이름', validators=[DataRequired(message="이용권 이름을 입력해주세요."), Length(max=150)],
                       description="템플릿 선택 시 자동 생성될 수 있습니다. 직접 수정도 가능합니다.")

    start_date = DateField('이용 시작일', validators=[DataRequired(message="시작일을 선택해주세요.")],
                           format='%Y-%m-%d', widget=DateInput()) # format 지정, DateInput 위젯 사용

    # 기간권/종합권 (템플릿 미사용 시)
    duration_days_manual = IntegerField('유효 기간 (일 수)', validators=[Optional(), NumberRange(min=1)],
                                     description="기간제 상품 직접 입력 시. (예: 30, 90)")

    # 횟수권/쿠폰/레슨추가/종합권 (템플릿 미사용 시)
    total_taseok_count_manual = IntegerField('총 타석 횟수', validators=[Optional(), NumberRange(min=1)],
                                           description="횟수제 상품 직접 입력 시 (타석).")
    total_lesson_count_manual = IntegerField('총 레슨 횟수', validators=[Optional(), NumberRange(min=0)], # 0회도 가능 (타석만 이용권)
                                            description="횟수제 상품 직접 입력 시 (레슨).")
    # 횟수제 유효기간 (템플릿 미사용 시)
    validity_days_manual = IntegerField('횟수제 유효기간 (일 수)', validators=[Optional(), NumberRange(min=1)],
                                      description="횟수제 상품 직접 입력 시 유효 기간.")
    # --- 여기까지 직접 입력 필드 ---

    pro_id = SelectField('담당 프로 (선택 사항)', coerce=coerce_int_or_none, validators=[Optional()])
    # pro_id의 choices도 라우트에서 동적으로 채워줍니다.

    price = IntegerField('실제 판매 가격 (원)', validators=[Optional(), NumberRange(min=0)])
    memo = TextAreaField('메모 (선택 사항)')
    submit = SubmitField('이용권 발급')

    # (선택적) 발급 폼 유효성 검사 로직 추가 가능
    # 예: 템플릿을 선택하지 않았을 경우, 직접 입력 필드들이 제대로 채워졌는지 등
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        is_template_selected = bool(self.ticket_template_id.data)
        # 여기에 추가적인 복합 유효성 검사 로직을 넣을 수 있습니다.
        # 예를 들어, 템플릿을 선택하지 않았는데 필수 정보(기간 또는 횟수 등)가 누락된 경우
        # if not is_template_selected:
        #     if not self.duration_days_manual.data and not self.total_taseok_count_manual.data:
        #         self.name.errors.append("템플릿 미선택 시 기간 또는 총 타석 횟수 중 하나는 입력해야 합니다.")
        #         return False
        return True
    
class TicketEditForm(FlaskForm):
    """발급된 이용권 수정 폼"""
    # 수정 가능 필드
    name = StringField('이용권 이름', validators=[DataRequired(), Length(max=150)])
    # start_date = DateField('이용 시작일', validators=[DataRequired()], format='%Y-%m-%d', widget=DateInput()) # 시작일 수정은 정책 검토 필요 (만료일 연동 등 복잡성)
    # expiry_date = DateField('만료일', validators=[Optional()], format='%Y-%m-%d', widget=DateInput()) # 만료일 직접 수정 기능? (홀딩으로 관리하는 것이 원칙)

    # 잔여 횟수 직접 수정 (오류 정정용)
    remaining_taseok_count = IntegerField('남은 타석 횟수', validators=[Optional(), NumberRange(min=0)])
    remaining_lesson_count = IntegerField('남은 레슨 횟수', validators=[Optional(), NumberRange(min=0)])

    pro_id = SelectField('담당 프로', coerce=coerce_int_or_none, validators=[Optional()]) # coerce 함수 재사용
    price = IntegerField('판매 가격 (원)', validators=[Optional(), NumberRange(min=0)])
    memo = TextAreaField('메모')
    is_active = BooleanField('활성 상태', description="만료/소진 시 자동으로 비활성화됩니다. 강제로 비활성화할 수 있습니다.")

    submit = SubmitField('수정 내용 저장')

    # 총 횟수 필드 (정보 표시용 또는 수정용 - 정책 결정 필요)
    # total_taseok_count = IntegerField('총 타석 횟수', render_kw={'readonly': True}) # 읽기 전용 표시 예시
    # total_lesson_count = IntegerField('총 레슨 횟수', render_kw={'readonly': True})

    # 폼 초기화 시 pro_id choices 로딩 필요
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 프로 선택지 동적 로딩
        self.pro_id.choices = [('', '담당 프로 없음')] + \
                              [(p.id, p.name) for p in Pro.query.order_by(Pro.name).all()]
        
class HoldingForm(FlaskForm):
    """이용권 홀딩 추가/수정 폼"""
    # ticket_id는 폼 외부에서 받아오므로 필드로 둘 필요 없음
    start_date = DateField('홀딩 시작일', validators=[DataRequired(message="시작일을 선택해주세요.")],
                           format='%Y-%m-%d', widget=DateInput())
    end_date = DateField('홀딩 종료일', validators=[DataRequired(message="종료일을 선택해주세요.")],
                         format='%Y-%m-%d', widget=DateInput())
    reason = StringField('홀딩 사유 (선택 사항)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('홀딩 저장')

    # 종료일이 시작일보다 이전인지 검증
    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError('홀딩 종료일은 시작일보다 이전일 수 없습니다.')


class BookingForm(FlaskForm):
    """관리자 예약 생성/수정 폼"""
    # coerce 함수 적용
    user_id = SelectField('회원', coerce=coerce_int_or_none, validators=[DataRequired(message="회원을 선택해주세요.")])
    booth_id = SelectField('타석', coerce=coerce_int_or_none, validators=[DataRequired(message="타석을 선택해주세요.")])
    booking_type = SelectField('예약 유형', coerce=BookingType, validators=[DataRequired()],
                               choices=[(t, t.value) for t in BookingType])
    # coerce 함수 적용
    pro_id = SelectField('담당 프로 (레슨 예약 시)', coerce=coerce_int_or_none, validators=[Optional()])

    # 날짜와 시간을 함께 입력받는 필드
    start_time = DateTimeLocalField('시작 시간', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], widget=DateTimeLocalInput())
    end_time = DateTimeLocalField('종료 시간', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], widget=DateTimeLocalInput())
    memo = TextAreaField('메모 (선택 사항)')
    submit = SubmitField('예약 생성')

    # choices는 라우트에서 동적으로 로드

    # 시작 시간/종료 시간 유효성 검증
    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('종료 시간은 시작 시간보다 이후여야 합니다.')
            # 최소/최대 예약 시간 검증 등 추가 가능

    # 레슨 예약 시 프로 선택 유효성 검증
    def validate_pro_id(self, field):
        if self.booking_type.data == BookingType.LESSON and not field.data:
            raise ValidationError('레슨 예약 시 담당 프로를 선택해야 합니다.')
        
