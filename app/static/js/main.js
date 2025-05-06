// app/static/js/main.js

// 전화번호 자동 하이픈 함수
function autoHyphenPhoneNumber(target) {
    let number = target.value.replace(/[^0-9]/g, ''); // 숫자 이외의 문자 모두 제거
    let phone = "";

    if (number.length < 4) {
        return number;
    } else if (number.length < 7) {
        phone += number.substr(0, 3);
        phone += "-";
        phone += number.substr(3);
    } else if (number.length < 11) {
        phone += number.substr(0, 3);
        phone += "-";
        phone += number.substr(3, 3);
        phone += "-";
        phone += number.substr(6);
    } else { // 11자리 이상 (예: 010-1234-5678)
        phone += number.substr(0, 3);
        phone += "-";
        phone += number.substr(3, 4);
        phone += "-";
        phone += number.substr(7, 4);
    }
    target.value = phone;
}

// 페이지 로드 후 전화번호 필드에 이벤트 리스너 추가
document.addEventListener('DOMContentLoaded', function() {
    // LoginForm의 phone 필드
    const loginPhoneField = document.querySelector('form input[name="phone"]'); // LoginForm 가정
    if (loginPhoneField) {
        loginPhoneField.addEventListener('input', function(e) {
            autoHyphenPhoneNumber(e.target);
        });
        // 선택사항: 포커스 아웃 시에도 한번 더 적용
        loginPhoneField.addEventListener('blur', function(e) {
             autoHyphenPhoneNumber(e.target);
        });
    }

    // RegistrationForm의 phone 필드 (예시: ID가 'register_phone'이라고 가정)
    // 실제로는 해당 폼의 phone 필드를 정확히 선택해야 합니다.
    // 예를 들어, 폼에 id="registrationForm" 이 있다면:
    // const registrationForm = document.getElementById('registrationForm');
    // if (registrationForm) {
    //     const registerPhoneField = registrationForm.querySelector('input[name="phone"]');
    //     if (registerPhoneField) {
    //         registerPhoneField.addEventListener('input', function(e) { /* ... */ });
    //         registerPhoneField.addEventListener('blur', function(e) { /* ... */ });
    //     }
    // }

    // 만약 모든 'phone' 이라는 name을 가진 input에 적용하고 싶다면:
    const phoneInputs = document.querySelectorAll('input[name="phone"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            autoHyphenPhoneNumber(e.target);
        });
         input.addEventListener('blur', function(e) {
             autoHyphenPhoneNumber(e.target);
        });
    });
});