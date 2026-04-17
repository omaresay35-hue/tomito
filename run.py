#!/usr/bin/env python3
import os
import subprocess

def clear():
    os.system('clear')

def menu():
    while True:
        clear()
        print("="*40)
        print("   🤖 TOMITO — Bot Runner (Manual Push)")
        print("="*40)
        print("1. 🚀 Run 500 New Pages (Unified Bot - Fast)")
        print("2. 🛠️  Fix Broken Links (Generate Missing Pages)")
        print("3. 🏗️  Update Homepage & Genres Only")
        print("4. 🌏 Update Google Search Index")
        print("-" * 40)
        print("p. 📤 Manual Git Pull/Push (Sync Changes)")
        print("q. ❌ Quit")
        print("="*40)
        
        choice = input("\nChoose an option: ").strip().lower()

        if choice == '1':
            subprocess.run(["python3", "unified_bot.py"])
        elif choice == '2':
            subprocess.run(["python3", "gen_missing.py"])
        elif choice == '3':
            subprocess.run(["python3", "build_homepage.py"])
        elif choice == '4':
            subprocess.run(["python3", "google_indexer.py"])
        elif choice == 'p':
            print("\n🔄 Pulling latest changes...")
            subprocess.run(["git", "pull", "origin", "main"])
            print("\n🚀 Pushing local changes...")
            subprocess.run(["bash", "git_sync.sh"])
        elif choice == 'q':
            print("\nGoodbye!")
            break
        else:
            print("\n❌ Invalid choice. Press Enter to continue.")
            input()

if __name__ == "__main__":
    menu()
