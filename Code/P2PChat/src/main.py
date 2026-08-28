#!/usr/bin/env python3
"""
UDM_9_CHAT-P2P - Main Entry Point
==================================

Ứng dụng P2P Chat với E2EE encryption (End-to-End Encrypted)
- True P2P architecture (No relay server needed)
- RSA 2048-bit + Fernet (AES) encryption
- GUI interface (PySide6)
- CLI interface
- File transfer with encryption
- Digital signature verification

Usage:
    python main.py --help
    python main.py gui                                    # GUI mode
    python main.py p2p --name Alice --port 5001          # P2P CLI mode
    python main.py test                                   # Run tests
"""

import sys
import argparse
import subprocess
import os
from pathlib import Path

# Ensure repo root is importable when this file is launched directly as a script
for parent in Path(__file__).resolve().parents:
    if (parent / "Code").exists():
        sys.path.insert(0, str(parent))
        break


# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """In banner chào mừng"""
    banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║           UDM_9_CHAT-P2P - Secure P2P Chat                  ║
║                                                              ║
║  • True Peer-to-Peer (No server relay)                       ║
║  • End-to-End Encrypted (RSA 2048 + Fernet AES)             ║
║  • Digital Signature Verification                           ║
║  • File Transfer with Encryption                            ║
║  • GUI & CLI Interfaces                                     ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
"""
    print(banner)


def print_help():
    """In trợ giúp"""
    help_text = f"""
{Colors.BOLD}Available Commands:{Colors.ENDC}

  {Colors.OKBLUE}gui{Colors.ENDC}
    Khởi chạy giao diện GUI (PySide6)
    
    {Colors.OKGREEN}Ví dụ:{Colors.ENDC}
      python main.py gui

  {Colors.OKBLUE}p2p{Colors.ENDC}
    Khởi chạy P2P Peer CLI (Chat trực tiếp peer-to-peer)
    
    {Colors.OKGREEN}Options:{Colors.ENDC}
      --name NAME         Tên của Peer (bắt buộc)
      --host HOST         IP để listening (default: 127.0.0.1)
      --port PORT         Port để listening (default: 5000)
      --no-secure         Không dùng E2EE encryption
    
    {Colors.OKGREEN}Ví dụ:{Colors.ENDC}
      python main.py p2p --name Alice --port 5001 --secure
      python main.py p2p --name Bob --port 5002 --secure

  {Colors.OKBLUE}test{Colors.ENDC}
    Chạy toàn bộ unit tests
    
    {Colors.OKGREEN}Options:{Colors.ENDC}
      --verbose, -v       Chế độ chi tiết
      --pattern PATTERN   Chỉ chạy test matching pattern
    
    {Colors.OKGREEN}Ví dụ:{Colors.ENDC}
      python main.py test
      python main.py test --verbose
      python main.py test -p test_crypto

  {Colors.OKBLUE}demo{Colors.ENDC}
    Chạy demo P2P integration test
    
    {Colors.OKGREEN}Ví dụ:{Colors.ENDC}
      python main.py demo

  {Colors.OKBLUE}info{Colors.ENDC}
    Hiển thị thông tin dự án
    
    {Colors.OKGREEN}Ví dụ:{Colors.ENDC}
      python main.py info

{Colors.BOLD}Quick Start:{Colors.ENDC}

  1. {Colors.OKCYAN}Chạy GUI:{Colors.ENDC}
     python main.py gui

  2. {Colors.OKCYAN}Chạy P2P Chat (2 terminals):{Colors.ENDC}
     # Terminal 1 - Alice
     python main.py p2p --name Alice --port 5001
     
     # Terminal 2 - Bob
     python main.py p2p --name Bob --port 5002
     # Trong Bob: /connect Alice 127.0.0.1 5001

  3. {Colors.OKCYAN}Chạy Tests:{Colors.ENDC}
     python main.py test

  4. {Colors.OKCYAN}Chạy Demo:{Colors.ENDC}
     python main.py demo
"""
    print(help_text)


def run_gui():
    """Chạy GUI application"""
    print(f"{Colors.OKCYAN}Khởi chạy GUI...{Colors.ENDC}")
    try:
        from Code.P2PChat.src.gui.main_qt_p2p_gui import main
        main()
    except ImportError as e:
        print(f"{Colors.FAIL}✗ Lỗi: Không tìm thấy PySide6{Colors.ENDC}")
        print(f"  Cài đặt: pip install PySide6")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.FAIL}✗ Lỗi chạy GUI: {e}{Colors.ENDC}")
        sys.exit(1)


def run_p2p(args):
    """Chạy P2P Peer CLI"""
    if not args.name:
        print(f"{Colors.FAIL}✗ Lỗi: --name là bắt buộc{Colors.ENDC}")
        sys.exit(1)
    
    print(f"{Colors.OKCYAN}Khởi chạy P2P Peer: {args.name}{Colors.ENDC}")
    try:
        from Code.P2PChat.src.p2p_peer import P2PPeer, interactive_peer_cli
        
        peer = P2PPeer(
            peer_name=args.name,
            listen_host=args.host,
            listen_port=args.port,
            secure=not args.no_secure
        )
        peer.start_listening()
        interactive_peer_cli(peer)
    
    except ImportError as e:
        print(f"{Colors.FAIL} Lỗi import: {e}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.FAIL} Lỗi chạy P2P: {e}{Colors.ENDC}")
        sys.exit(1)


def run_tests(args):
    """Chạy unit tests"""
    print(f"{Colors.OKCYAN}Khởi chạy unit tests...{Colors.ENDC}\n")
    
    test_dir = Path("Code/P2PChat/src/test")
    if not test_dir.exists():
        print(f"{Colors.FAIL} Không tìm thấy test directory{Colors.ENDC}")
        sys.exit(1)
    
    try:
        import unittest
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load tất cả tests
        suite.addTests(loader.discover(str(test_dir), pattern="test_*.py"))
        
        verbosity = 2 if args.verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        # In kết quả
        print("\n" + "="*60)
        if result.wasSuccessful():
            print(f"{Colors.OKGREEN}✓ Tất cả tests đã pass!{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}✗ Có {len(result.failures)} failures, {len(result.errors)} errors{Colors.ENDC}")
        print("="*60)
        
        sys.exit(0 if result.wasSuccessful() else 1)
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ Lỗi chạy tests: {e}{Colors.ENDC}")
        sys.exit(1)


def run_demo():
    """Chạy integration demo"""
    print(f"{Colors.OKCYAN}Khởi chạy Integration Demo...{Colors.ENDC}\n")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "Code/P2PChat/src/test_integration.py"],
            cwd=Path.cwd()
        )
        sys.exit(result.returncode)
    
    except Exception as e:
        print(f"{Colors.FAIL} Lỗi chạy demo: {e}{Colors.ENDC}")
        sys.exit(1)


def print_project_info():
    """In thông tin dự án"""
    info = f"""
{Colors.BOLD}📋 Thông Tin Dự Án{Colors.ENDC}

{Colors.OKCYAN}Tên:{Colors.ENDC} UDM_9_CHAT-P2P
{Colors.OKCYAN}Loại:{Colors.ENDC} True Peer-to-Peer Chat Application
{Colors.OKCYAN}Ngôn ngữ:{Colors.ENDC} Python 3.10+
{Colors.OKCYAN}Platform:{Colors.ENDC} Windows / Linux / macOS

{Colors.BOLD}🔐 Tính Năng Bảo Mật{Colors.ENDC}

  • RSA 2048-bit encryption (Asymmetric)
  • Fernet (AES) encryption (Symmetric)
  • End-to-End Encryption (E2EE)
  • Digital Signature (SHA-256 + RSA-PSS)
  • Key Fingerprint verification (SHA-256)
  • Perfect Forward Secrecy (PFS) via session key

{Colors.BOLD}📂 Cấu Trúc Thư Mục{Colors.ENDC}

  Code/P2PChat/src/
  ├── crypto.py              - RSA & Fernet crypto manager
  ├── handshake.py           - E2EE handshake protocol
  ├── transfer.py            - File transfer with encryption
  ├── p2p_peer.py            - True P2P peer implementation
  ├── test_integration.py    - Integration tests
  ├── message/
  │   └── protocol.py        - Message framing & serialization
  ├── netWork/
  │   └── node.py            - (Deprecated relay server)
  ├── gui/                   - PySide6 GUI components
  └── test/                  - Unit tests

{Colors.BOLD}👥 Thành Viên Nhóm{Colors.ENDC}

  • Huỳnh Văn Tại (054206000426)
  • Ngô Đặng Minh Khôi (089206018408)
  • Trần Ngô Duy Khang (082206013072)
  • Ngủ Hoàng Khang (089206018080)
  • Nguyễn Thanh Khánh (040206012006)
  • Lương Quốc Khánh (051206012692)

{Colors.BOLD}🎯 Yêu Cầu Dependencies{Colors.ENDC}

  - cryptography>=41.0.0
  - PySide6>=6.5.0 (cho GUI)

  Cài đặt:
    pip install -r requirements.txt

{Colors.BOLD}⚡ Kiến Trúc P2P{Colors.ENDC}

  Peer A ◄────────────────────────────► Peer B
       (Direct TCP, E2EE Handshake)
  
  ✓ Decentralized - Không cần relay server
  ✓ Direct connection - Giao tiếp trực tiếp
  ✓ End-to-End encryption - Bảo mật toàn bộ
  ✓ Peer discovery - Tìm kiếm peer trong mạng

{Colors.BOLD}📚 Tài Liệu Thêm{Colors.ENDC}

  - README.md                    Hướng dẫn sử dụng chi tiết
  - DOCX/phân công.docx          Phân công công việc
  - PPTX/phân công.docx          Bài thuyết trình
"""
    print(info)


def main():
    """Main entry point"""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="UDM_9_CHAT-P2P - Secure P2P Chat Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Use 'python main.py <command> --help' for more information"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # GUI command
    gui_parser = subparsers.add_parser("gui", help="Chạy GUI application")
    
    # P2P command
    p2p_parser = subparsers.add_parser("p2p", help="Chạy P2P Peer CLI")
    p2p_parser.add_argument("--name", required=True, help="Tên của Peer")
    p2p_parser.add_argument("--host", default="127.0.0.1", help="Host để listening")
    p2p_parser.add_argument("--port", type=int, default=5000, help="Port để listening")
    p2p_parser.add_argument("--no-secure", action="store_true", help="Không dùng encryption")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Chạy unit tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    test_parser.add_argument("-p", "--pattern", default="test_*.py", help="Test pattern")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Chạy integration demo")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Hiển thị thông tin dự án")
    
    args = parser.parse_args()
    
    if not args.command:
        print_help()
        sys.exit(0)
    
    if args.command == "gui":
        run_gui()
    
    elif args.command == "p2p":
        run_p2p(args)
    
    elif args.command == "test":
        run_tests(args)
    
    elif args.command == "demo":
        run_demo()
    
    elif args.command == "info":
        print_project_info()
    
    else:
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠ Đã thoát{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.FAIL}✗ Lỗi không xác định: {e}{Colors.ENDC}")
        sys.exit(1)
