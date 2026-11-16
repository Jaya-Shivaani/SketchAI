import os
import sys
import subprocess

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    backend_main = os.path.join(root_dir, "Backend", "main.py")

    print("=" * 60)
    print("  🚀 Starting SketchAI Collaborative Drawing Game Platform")
    print("=" * 60)
    print(f"Working Directory: {root_dir}")
    print(f"Python Executable: {sys.executable}")
    print(f"Target Script:     {backend_main}")
    print("-" * 60)

    try:
        subprocess.run([sys.executable, backend_main], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped gracefully by user.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
