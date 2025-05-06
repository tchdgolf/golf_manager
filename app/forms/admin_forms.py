# app/forms/admin_forms.py
from wtforms import StringField, SubmitField, SelectField, BooleanField, TextAreaField, PasswordField # PasswordField 추가
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, ValidationError, Email # Email 추가 (필요시)
from app.models import Pro, Booth, User # Booth 모델 임포트 # Pro 모델 임포트 (중복 검사용)
from app.models.enums import BoothSystemType # Enum 임포트


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