# app/forms/admin_forms.py
from wtforms import StringField, SubmitField, SelectField, BooleanField, TextAreaField, PasswordField, IntegerField, DateField
from flask_wtf import FlaskForm
from wtforms.widgets import DateInput 
from wtforms.validators import DataRequired, Length, ValidationError, Email, Optional, NumberRange
from app.models import Pro, Booth, User, TicketTemplate, Ticket
from app.models.enums import BoothSystemType # Enum 임포트
from app.models.ticket_template import TicketCategory 



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

    ticket_template_id = SelectField('템플릿 선택 (선택 사항)', coerce=int, validators=[Optional()])
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

    pro_id = SelectField('담당 프로 (선택 사항)', coerce=int, validators=[Optional()])
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