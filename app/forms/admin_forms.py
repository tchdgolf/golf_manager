# app/forms/admin_forms.py
from wtforms import StringField, SubmitField, SelectField, BooleanField, TextAreaField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, ValidationError
from app.models import Pro, Booth # Booth 모델 임포트 # Pro 모델 임포트 (중복 검사용)
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

# Booth, User 관련 폼들도 나중에 여기에 추가...