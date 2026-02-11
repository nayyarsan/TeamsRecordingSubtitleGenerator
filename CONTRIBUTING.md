# Contributing to Webex Speaker Labeling Tool

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Detailed description of the problem or suggestion
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs (use `--verbose` flag)

### Submitting Changes

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add/update tests as needed
   - Update documentation if needed
   - Add comments for complex logic

4. **Test your changes**
   ```bash
   # Run tests (when available)
   pytest
   
   # Verify code style
   black src/
   flake8 src/
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "Add feature: brief description"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Pull Request Guidelines

- **One feature per PR** - Keep PRs focused
- **Clear description** - Explain what and why
- **Update docs** - If behavior changes
- **Add tests** - For new features
- **Pass CI checks** - Ensure tests pass

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/webex-speaker-labeling.git
cd webex-speaker-labeling

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Set up pre-commit hooks (optional)
pre-commit install
```

## Code Style

- **Python**: Follow PEP 8
- **Formatting**: Use `black` for auto-formatting
- **Linting**: Use `flake8` for linting
- **Type hints**: Add type hints for functions
- **Docstrings**: Use Google-style docstrings

Example:
```python
def process_segment(
    segment: DiarizationSegment,
    config: Dict[str, Any]
) -> SpeakerSegment:
    """
    Process a diarization segment.
    
    Args:
        segment: Input diarization segment
        config: Configuration dictionary
    
    Returns:
        Processed speaker segment
    
    Raises:
        ValueError: If segment is invalid
    """
    pass
```

## Testing

When adding features:

1. **Add unit tests** for individual functions
2. **Add integration tests** for module interactions
3. **Test edge cases** (empty input, invalid data, etc.)
4. **Test error handling**

```python
# Example test
def test_audio_extraction():
    processor = AudioProcessor()
    audio_path = processor.extract_audio(test_video_path)
    assert audio_path.exists()
    assert audio_path.suffix == '.wav'
```

## Documentation

Update relevant docs when making changes:

- **README.md** - For user-facing changes
- **USAGE.md** - For new features or workflows
- **ARCHITECTURE.md** - For structural changes
- **Inline comments** - For complex logic
- **Docstrings** - For all public functions

## Areas for Contribution

### High Priority
- [ ] Unit and integration tests
- [ ] Performance optimization
- [ ] Better name extraction algorithms
- [ ] Manual speaker override feature
- [ ] GPU acceleration support

### Medium Priority
- [ ] Web UI
- [ ] Batch processing utilities
- [ ] Additional output formats
- [ ] Multi-language support
- [ ] Better error messages

### Low Priority
- [ ] VS Code extension
- [ ] Electron desktop app
- [ ] Real-time processing
- [ ] Advanced analytics

## Questions?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar questions

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on the code, not the person
- Assume good intentions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
