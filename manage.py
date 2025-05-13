import os
import argparse
from tools.general.vite import start_vite

def check_pnpm():
    if os.system("pnpm --version") != 0:
        print("pnpm could not be found")
        print("Please install node and pnpm")
        print("https://nodejs.org/en/download")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Manage the GOT Counter app.")
    parser.add_argument("mode", choices=["dev", "prod", "generate:api"], help="Run mode")
    args = parser.parse_args()
    
    check_pnpm()

    if args.mode == "dev":
        # Start Vite dev server and capture stdout
        import tools.interface.converter as converter
        converter.convert_live()
        port, _ = start_vite()
        import app.main as main
        main.start(f"http://localhost:{port}", debug=True)
    elif args.mode == "generate:api":
        import tools.interface.converter as converter
        converter.convert()
    elif args.mode == "prod":
        pass

if __name__ == "__main__":
    main()
    