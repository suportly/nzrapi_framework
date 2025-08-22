"""
Tests for simple authentication utilities
"""

import pytest

from nzrapi.security import check_password_hash, create_password_hash, simple_hash_password, simple_verify_password


class TestSimpleAuth:
    """Test the simple authentication utilities"""

    def test_create_password_hash(self):
        """Test password hash creation"""
        password = "test_password_123"
        hash_str = create_password_hash(password)

        # Should return a string with hash:salt format
        assert isinstance(hash_str, str)
        assert ":" in hash_str
        assert len(hash_str) > 20  # Should be reasonably long

        # Should be different each time due to random salt
        hash_str2 = create_password_hash(password)
        assert hash_str != hash_str2

    def test_check_password_hash_correct_password(self):
        """Test password verification with correct password"""
        password = "correct_password"
        hash_str = create_password_hash(password)

        # Should return True for correct password
        assert check_password_hash(password, hash_str) is True

    def test_check_password_hash_incorrect_password(self):
        """Test password verification with incorrect password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hash_str = create_password_hash(password)

        # Should return False for incorrect password
        assert check_password_hash(wrong_password, hash_str) is False

    def test_check_password_hash_malformed_hash(self):
        """Test password verification with malformed hash"""
        password = "test_password"
        malformed_hash = "invalid_hash_without_colon"

        # Should return False for malformed hash
        assert check_password_hash(password, malformed_hash) is False

    def test_simple_password_aliases(self):
        """Test that the aliases work correctly"""
        password = "test_password_456"

        # Test alias functions
        hash_str = simple_hash_password(password)
        assert isinstance(hash_str, str)
        assert ":" in hash_str

        # Test verification alias
        assert simple_verify_password(password, hash_str) is True
        assert simple_verify_password("wrong", hash_str) is False

    def test_hash_different_passwords(self):
        """Test that different passwords produce different hashes"""
        password1 = "password1"
        password2 = "password2"

        hash1 = create_password_hash(password1)
        hash2 = create_password_hash(password2)

        # Different passwords should produce different hashes
        assert hash1 != hash2

        # Each should verify correctly
        assert check_password_hash(password1, hash1) is True
        assert check_password_hash(password2, hash2) is True

        # Cross-verification should fail
        assert check_password_hash(password1, hash2) is False
        assert check_password_hash(password2, hash1) is False

    def test_empty_password(self):
        """Test handling of empty password"""
        empty_password = ""
        hash_str = create_password_hash(empty_password)

        # Should still create a hash
        assert isinstance(hash_str, str)
        assert ":" in hash_str

        # Should verify correctly
        assert check_password_hash(empty_password, hash_str) is True
        assert check_password_hash("not_empty", hash_str) is False

    def test_unicode_password(self):
        """Test handling of unicode passwords"""
        unicode_password = "пароль123äöü"
        hash_str = create_password_hash(unicode_password)

        # Should work with unicode
        assert isinstance(hash_str, str)
        assert ":" in hash_str

        # Should verify correctly
        assert check_password_hash(unicode_password, hash_str) is True
        assert check_password_hash("regular_password", hash_str) is False
