"""
CLI Interface for OSRS Wiki RAG System
Terminal-based continuous Q&A interface.
"""

import sys
from rag_system import RAGSystem


def main():
    """Main CLI loop."""
    print("=" * 60)
    print("OSRS Wiki RAG System - CLI Interface")
    print("=" * 60)
    print("\nInitializing RAG system...")
    
    try:
        rag = RAGSystem()
        print("[OK] RAG system ready!\n")
    except Exception as e:
        print(f"[ERROR] Error initializing RAG system: {e}")
        sys.exit(1)
    
    print("Type your questions about Old School RuneScape.")
    print("\nCommands:")
    print("  - Type 'quit' or 'exit' to exit")
    print("  - Type 'clear' to clear the screen")
    print("  - Type 'logs' to view query log count")
    print("  - Type 'clearlogs' to clear query logs")
    print("\nNote: Rate limiting is enabled (max 1 query per 2 seconds)")
    print("-" * 60)
    
    user_id = "cli_user"  # Simple user ID for CLI
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if query.lower() == 'clear':
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            if query.lower() == 'logs':
                log_count = rag.security_manager.get_log_count()
                print(f"\nTotal queries logged: {log_count}")
                continue
            
            if query.lower() == 'clearlogs':
                if rag.security_manager.clear_logs():
                    print("\n[OK] Query logs cleared")
                else:
                    print("\n[ERROR] Failed to clear logs")
                continue
            
            # Process query
            print("\nSearching...")
            result = rag.query(query, user_id=user_id)
            
            # Check for errors
            if result.get('rejected'):
                print("\n" + "=" * 60)
                print("QUERY REJECTED:")
                print("=" * 60)
                print(result['answer'])
                print("\n" + "=" * 60)
                continue
            
            if result.get('error') == 'rate_limit':
                wait_time = result.get('wait_time', 2.0)
                print("\n" + "=" * 60)
                print("RATE LIMIT:")
                print("=" * 60)
                print(result['answer'])
                print(f"\nPlease wait {wait_time:.1f} seconds before trying again.")
                print("=" * 60)
                continue
            
            # Display answer
            print("\n" + "=" * 60)
            print("ANSWER:")
            print("=" * 60)
            print(result['answer'])
            
            # Display sources
            if result.get('sources'):
                print("\n" + "-" * 60)
                print("SOURCES:")
                print("-" * 60)
                for i, source in enumerate(result['sources'], 1):
                    print(f"{i}. {source}")
            
            print("\n" + "=" * 60)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            print("Please try again or type 'quit' to exit.")


if __name__ == "__main__":
    main()
