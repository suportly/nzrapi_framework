#!/bin/bash

# NzrApi Framework - PyPI Publication Script
# This script automates the process of building and publishing the package to PyPI

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get current version from pyproject.toml
get_current_version() {
    python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
}

# Function to check if working directory is clean
check_git_clean() {
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Working directory is not clean"
        git status --porcelain
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Aborted"
            exit 1
        fi
    fi
}

# Function to validate version format
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+(\.[0-9]+)?)?$ ]]; then
        print_error "Invalid version format: $version"
        print_error "Expected format: X.Y.Z or X.Y.Z-prerelease"
        exit 1
    fi
}

# Function to load environment variables and configure Twine
configure_pypi_auth() {
    print_status "Configuring PyPI authentication..."
    if [ -f ".env" ]; then
        print_status "Found .env file, loading variables..."
        # Export variables from .env file, ignoring comments
        set -o allexport
        source .env
        set +o allexport
    else
        print_warning ".env file not found. Make sure PYPI_API_TOKEN is set in your environment."
    fi

    if [ -z "$PYPI_API_TOKEN" ]; then
        print_error "PYPI_API_TOKEN is not set. Cannot publish."
        exit 1
    fi

    export TWINE_USERNAME="__token__"
    export TWINE_PASSWORD="$PYPI_API_TOKEN"
    print_success "PyPI authentication configured."
}

# Main script starts here
main() {
    print_status "🚀 Starting NzrApi Framework publication process..."
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! command_exists python; then
        print_error "Python is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists git; then
        print_error "Git is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found. Make sure you're in the project root directory."
        exit 1
    fi
    
    # Check git repository
    check_git_repo
    
    # Get current version
    CURRENT_VERSION=$(get_current_version)
    print_status "Current version: $CURRENT_VERSION"
    
    # Parse command line arguments
    PUBLISH_TYPE="test"  # default to test PyPI
    NEW_VERSION=""
    SKIP_TESTS=false
    SKIP_BUILD_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --production|--prod)
                PUBLISH_TYPE="production"
                shift
                ;;
            --test)
                PUBLISH_TYPE="test"
                shift
                ;;
            --version)
                NEW_VERSION="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-build-check)
                SKIP_BUILD_CHECK=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --production, --prod    Publish to production PyPI (default: test PyPI)"
                echo "  --test                  Publish to test PyPI (default)"
                echo "  --version VERSION       Set new version before publishing"
                echo "  --skip-tests           Skip running tests"
                echo "  --skip-build-check     Skip build verification"
                echo "  --help, -h             Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                                    # Publish to test PyPI"
                echo "  $0 --production                       # Publish to production PyPI"
                echo "  $0 --version 1.2.0 --production      # Update version and publish to production"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Update version if specified
    if [ -n "$NEW_VERSION" ]; then
        validate_version "$NEW_VERSION"
        print_status "Updating version to $NEW_VERSION..."
        
        # Update version in pyproject.toml
        sed -i "s/version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
        
        # Update version in __init__.py
        sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" nzrapi/__init__.py
        
        print_success "Version updated to $NEW_VERSION"
        CURRENT_VERSION=$NEW_VERSION
    fi
    
    # Check for uncommitted changes
    check_git_clean
    
    # Install/upgrade build tools
    print_status "Installing/upgrading build tools..."
    python -m pip install --upgrade pip
    python -m pip install --upgrade build twine
    
    # Run tests (unless skipped)
    if [ "$SKIP_TESTS" = false ]; then
        print_status "Running tests..."
        if [ -f "requirements-dev.txt" ]; then
            python -m pip install -r requirements-dev.txt
        else
            python -m pip install -e ".[dev]"
        fi
        
        # Run linting
        print_status "Running code quality checks..."
        python -m black --check . || {
            print_error "Code formatting issues found. Run 'black .' to fix."
            exit 1
        }
        
        python -m isort --check-only . || {
            print_error "Import sorting issues found. Run 'isort .' to fix."
            exit 1
        }
        
        python -m flake8 . || {
            print_error "Linting issues found."
            exit 1
        }
        
        # Run type checking
        python -m mypy nzrapi || {
            print_warning "Type checking issues found."
        }
        
        # Run tests
        python -m pytest || {
            print_error "Tests failed."
            exit 1
        }
        
        print_success "All tests passed!"
    else
        print_warning "Skipping tests as requested"
    fi
    
    # Clean previous builds
    print_status "Cleaning previous builds..."
    rm -rf build/ dist/ *.egg-info/
    
    # Build the package
    print_status "Building package..."
    python -m build
    
    # Verify build
    if [ "$SKIP_BUILD_CHECK" = false ]; then
        print_status "Verifying build..."
        python -m twine check dist/*
        print_success "Build verification passed!"
    else
        print_warning "Skipping build verification as requested"
    fi
    
    # Show what will be uploaded
    print_status "Package contents:"
    ls -la dist/
    
    # Configure authentication before asking for confirmation
    configure_pypi_auth

    # Confirm publication
    if [ "$PUBLISH_TYPE" = "production" ]; then
        print_warning "⚠️  You are about to publish to PRODUCTION PyPI!"
        print_warning "This action cannot be undone."
        echo ""
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Publication aborted"
            exit 1
        fi
    else
        print_status "Publishing to TEST PyPI..."
        read -p "Continue with test publication? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            print_error "Publication aborted"
            exit 1
        fi
    fi
    
    # Upload to PyPI
    if [ "$PUBLISH_TYPE" = "production" ]; then
        print_status "Uploading to production PyPI..."
        python -m twine upload dist/*
        PYPI_URL="https://pypi.org/project/nzrapi/$CURRENT_VERSION/"
    else
        print_status "Uploading to test PyPI..."
        python -m twine upload --repository testpypi dist/*
        PYPI_URL="https://test.pypi.org/project/nzrapi/$CURRENT_VERSION/"
    fi
    
    # Create git tag if publishing to production and version was updated
    if [ "$PUBLISH_TYPE" = "production" ] && [ -n "$NEW_VERSION" ]; then
        print_status "Creating git tag..."
        git add pyproject.toml nzrapi/__init__.py
        git commit -m "chore: bump version to $NEW_VERSION"
        git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"
        
        print_status "Pushing changes and tags to repository..."
        git push origin main
        git push origin "v$NEW_VERSION"
        
        print_success "Git tag v$NEW_VERSION created and pushed!"
    fi
    
    # Success message
    print_success "🎉 Package published successfully!"
    echo ""
    print_status "Package details:"
    echo "  📦 Package: nzrapi"
    echo "  🏷️  Version: $CURRENT_VERSION"
    echo "  🌐 URL: $PYPI_URL"
    echo ""
    
    if [ "$PUBLISH_TYPE" = "test" ]; then
        print_status "To install from test PyPI:"
        echo "  pip install -i https://test.pypi.org/simple/ nzrapi==$CURRENT_VERSION"
    else
        print_status "To install from PyPI:"
        echo "  pip install nzrapi==$CURRENT_VERSION"
    fi
    
    echo ""
    print_success "Publication complete! 🚀"
}

# Run main function with all arguments
main "$@"