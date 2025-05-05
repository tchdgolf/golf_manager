import keyboard
import subprocess

def git_auto_push():
    print("🔤 커밋 메시지를 입력하세요:")
    message = input("> ")
    
    try:
        subprocess.run(["git", "status"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", message])
        subprocess.run(["git", "push"])
        print("✅ Push 완료!")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

print("👀 'a' 키를 누르면 Git 자동 커밋/푸시가 실행됩니다. 종료하려면 Ctrl+C 누르세요.")

# 'a' 키가 눌렸을 때 함수 실행
keyboard.add_hotkey('a', git_auto_push)

# 프로그램이 계속 실행되도록 유지
keyboard.wait()
