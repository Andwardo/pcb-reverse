# Contributing to PCB Reverse Engineering Tool

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive in all interactions. We're here to build something useful together.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Sample data if applicable

### Suggesting Features

1. Check if the feature has been requested in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear description of the feature
   - Use case / why it's useful
   - Proposed implementation (optional)

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly with various edge cases
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where helpful
- Keep functions focused and under 50 lines when practical
- Add docstrings for public functions

### Design Principles

1. **Zero Dependencies**: This tool must work with Python standard library only
2. **Single File**: Keep the main tool in one file for easy distribution
3. **Backwards Compatible**: Don't break existing project file formats
4. **User Friendly**: Provide clear error messages and helpful feedback

### Testing

Before submitting:

1. Test with a new project
2. Test with existing project files
3. Test all export formats
4. Test edge cases (empty projects, special characters, etc.)

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Reference issues when applicable ("Fix #123: Handle empty values")

## File Format Changes

If your change affects the JSON file format:

1. Ensure backwards compatibility (read old formats)
2. Document the change in CHANGELOG.md
3. Update version number appropriately

## Adding Export Formats

To add a new export format:

1. Add an export method following the pattern of existing ones
2. Add a CLI command in the main loop
3. Update the help text
4. Add documentation to README.md
5. Add an example in the examples folder

## Questions?

Open an issue with the "question" label and we'll help you out.

## Recognition

Contributors will be acknowledged in the README and CHANGELOG. Thank you for helping make this tool better!
