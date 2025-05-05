# app/forms/auth_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from app.models import User # User 모델 임포트 (중복 확인 등)

class LoginForm(FlaskForm):
    """로그인 폼"""
    phone = StringField('연락처', validators=[
        DataRequired(message="연락처를 입력해주세요."),
        # 간단한 숫자+하이픈 형식 검증 (필요에 따라 정규식 수정)
        Regexp(r'^[\d-]+$', message="유효한 연락처 형식이 아닙니다. (숫자, 하이픈만 사용)")
    ], render_kw={"placeholder": "'-' 포함하여 입력"})
    password = PasswordField('비밀번호', validators=[DataRequired(message="비밀번호를 입력해주세요.")])
    remember_me = BooleanField('로그인 상태 유지')
    submit = SubmitField('로그인')

class RegistrationForm(FlaskForm):
    """회원 등록 폼 (관리자용)"""
    name = StringField('이름', validators=[
        DataRequired(message="이름을 입력해주세요."),
        Length(min=2, max=100, message="이름은 2자 이상 100자 이하로 입력해주세요.")
    ])
    phone = StringField('연락처', validators=[
        DataRequired(message="연락처를 입력해주세요."),
        Regexp(r'^[\d-]+$', message="유효한 연락처 형식이 아닙니다. (숫자, 하이픈만 사용)")
    ], render_kw={"placeholder": "'-' 포함하여 입력"})
    memo = TextAreaField('메모 (선택 사항)')
    submit = SubmitField('회원 등록')

    # 연락처 중복 검증 커스텀 validator
    def validate_phone(self, phone):
        user = User.query.filter_by(phone=phone.data).first()
        if user:
            raise ValidationError('이미 등록된 연락처입니다.')

# 비밀번호 변경 폼 (향후 마이페이지 등에서 사용)
# class ChangePasswordForm(FlaskForm):
#     old_password = PasswordField('현재 비밀번호', validators=[DataRequired()])
#     new_password = PasswordField('새 비밀번호', validators=[
#         DataRequired(),
#         Length(min=4, message="비밀번호는 4자 이상으로 설정해주세요.") # 최소 길이 예시
#     ])
#     confirm_password = PasswordField('새 비밀번호 확인', validators=[
#         DataRequired(),
#         EqualTo('new_password', message='새 비밀번호가 일치하지 않습니다.')
#     ])
#     submit = SubmitField('비밀번호 변경')

# 비밀번호 초기화 폼 (관리자용 - 필요시 추가)
# class ResetPasswordForm(FlaskForm):
#     submit = SubmitField('비밀번호 초기화 (0000)')