# app/forms/admin_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from app.models import Pro # Pro 모델 임포트 (중복 검사용)

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