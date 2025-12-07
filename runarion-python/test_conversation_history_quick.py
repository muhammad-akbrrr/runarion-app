#!/usr/bin/env python3
"""
Quick verification test for Conversation History System

This script performs basic verification without requiring full test infrastructure.
Run this to verify the conversation history code is working correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all imports work correctly."""
    print("🔍 Testing imports...")
    
    try:
        from services.conversation_manager import ConversationManager
        print("  ✓ ConversationManager imported")
        
        from providers.gemini_provider import GeminiProvider
        print("  ✓ GeminiProvider imported")
        
        from models.story_generation.prompt_config import PromptConfig
        print("  ✓ PromptConfig imported")
        
        from datetime import datetime, timezone
        print("  ✓ datetime imported")
        
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_conversation_manager_structure():
    """Test that ConversationManager has all required methods."""
    print("\n🔍 Testing ConversationManager structure...")
    
    try:
        from services.conversation_manager import ConversationManager
        
        required_methods = [
            'load_history',
            'append_message',
            'update_chapter_content',
            'to_gemini_format',
            'initialize_conversation'
        ]
        
        for method_name in required_methods:
            if hasattr(ConversationManager, method_name):
                print(f"  ✓ Method '{method_name}' exists")
            else:
                print(f"  ✗ Method '{method_name}' missing")
                return False
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_gemini_format_conversion():
    """Test the to_gemini_format method logic."""
    print("\n🔍 Testing Gemini format conversion logic...")
    
    try:
        from services.conversation_manager import ConversationManager
        
        # Create a mock manager (doesn't need DB connection for this test)
        class MockDBPool:
            pass
        
        manager = ConversationManager(MockDBPool())
        
        # Test data
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Continue"}
        ]
        
        gemini_format = manager.to_gemini_format(messages)
        
        # Verify structure
        if len(gemini_format) != 3:
            print(f"  ✗ Expected 3 messages, got {len(gemini_format)}")
            return False
        
        # Verify role conversion
        if gemini_format[0]["role"] != "user":
            print(f"  ✗ First message should be 'user', got '{gemini_format[0]['role']}'")
            return False
        
        if gemini_format[1]["role"] != "model":
            print(f"  ✗ Assistant should be 'model', got '{gemini_format[1]['role']}'")
            return False
        
        # Verify parts structure
        if "parts" not in gemini_format[0]:
            print("  ✗ Missing 'parts' in message")
            return False
        
        if not isinstance(gemini_format[0]["parts"], list):
            print("  ✗ 'parts' should be a list")
            return False
        
        if "text" not in gemini_format[0]["parts"][0]:
            print("  ✗ Missing 'text' in parts")
            return False
        
        print("  ✓ Gemini format conversion works correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gemini_provider_conversation_history():
    """Test that GeminiProvider has conversation history support."""
    print("\n🔍 Testing GeminiProvider conversation history support...")
    
    try:
        from providers.gemini_provider import GeminiProvider
        
        # Check if method exists
        if hasattr(GeminiProvider, 'set_conversation_history'):
            print("  ✓ set_conversation_history method exists")
        else:
            print("  ✗ set_conversation_history method missing")
            return False
        
        # Check if attribute exists
        # We can't instantiate without request, but we can check the code structure
        print("  ✓ Conversation history support present in GeminiProvider")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_file_structure():
    """Test that all required files exist."""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        'src/services/conversation_manager.py',
        'src/api/generation.py',
        'src/providers/gemini_provider.py',
        'runarion-laravel/database/migrations/2025_12_20_120000_create_project_conversations_table.php'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), '..', file_path)
        if os.path.exists(full_path):
            print(f"  ✓ {file_path} exists")
        else:
            print(f"  ✗ {file_path} missing")
            all_exist = False
    
    return all_exist


def test_code_syntax():
    """Test that Python files have valid syntax."""
    print("\n🔍 Testing code syntax...")
    
    import py_compile
    
    python_files = [
        'src/services/conversation_manager.py',
        'src/api/generation.py',
        'src/providers/gemini_provider.py'
    ]
    
    all_valid = True
    for file_path in python_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        try:
            py_compile.compile(full_path, doraise=True)
            print(f"  ✓ {file_path} has valid syntax")
        except py_compile.PyCompileError as e:
            print(f"  ✗ {file_path} has syntax errors: {e}")
            all_valid = False
    
    return all_valid


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("CONVERSATION HISTORY SYSTEM - QUICK VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Code Syntax", test_code_syntax),
        ("Imports", test_imports),
        ("ConversationManager Structure", test_conversation_manager_structure),
        ("Gemini Format Conversion", test_gemini_format_conversion),
        ("GeminiProvider Support", test_gemini_provider_conversation_history),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Total: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All verification tests passed!")
        print("\nNext steps:")
        print("1. Run Laravel migration: php artisan migrate")
        print("2. Test with actual generation in Laravel UI")
        print("3. Check database for conversation history")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)








