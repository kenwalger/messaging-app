# Contributing to Abiqua Asset Management

Thank you for your interest in contributing to Abiqua Asset Management (AAM). This document provides guidelines for contributing to the project.

## Code of Conduct

All contributors must:
- Follow the project's Legal & Ethical Constraints (Specification #4)
- Respect the Non-Goals & Prohibited Behaviors (Specification #2)
- Adhere to the Do Not Invent List (Specification #5)
- Maintain professional and respectful communication

## Development Process

### Specification-Driven Development

**Critical:** All code must be traceable to frozen specifications (Assets #1-#18). 

- Do not implement features not specified in the frozen specs
- Do not invent behaviors, values, or assumptions
- Reference spec IDs in code comments and commit messages
- If something is undefined, STOP and ask for clarification

### Branching Strategy

- **main**: Production-ready code
- **develop**: Integration branch for feature testing
- **feature/**: Feature branches (e.g., `feature/identity-provisioning`)
- **hotfix/**: Hotfix branches (e.g., `hotfix/message-expiration-bug`)

### Commit Messages

Commit messages must:
- Be in present tense
- Reference relevant spec ID or ADR ID
- Be deterministic and descriptive

**Format:**
```
Implement <feature> (Spec #X, ADR #Y)

Brief description of changes.

References:
- Functional Spec (#6), Section X.Y
- State Machines (#7), Section Z
```

**Example:**
```
Add message expiration enforcement (StateMachine-07)

Implement device-local expiration timers with 7-day default.
All expired messages deleted immediately upon expiration.

References:
- Functional Spec (#6), Section 4.4
- State Machines (#7), Section 7
- Resolved TBDs: Default expiration 7 days
```

## Coding Standards

### Python Code

- Follow PEP 8
- Use type hints where appropriate
- Include docstrings referencing spec IDs
- Maximum line length: 100 characters (soft limit)

### File Naming

- Python files: `snake_case.py` (e.g., `message_delivery.py`)
- Directories: `lowercase-with-hyphens/` (e.g., `backend/`)
- Test files: `test_<module>.py`

### Code Structure

```
src/
├── client/         # Operator device app code
├── backend/        # Backend relay and controller interfaces
└── shared/         # Shared utilities, types, constants
```

## Testing Requirements

### Test Coverage

- Minimum 80% coverage for critical modules (messaging, identity, state machines)
- All state machine transitions must be tested
- All edge cases from specifications must be tested

### Test Naming

Format: `<module>_<function>_<scenario>`

Example: `test_message_delivery_create_message_success`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_message_delivery.py::TestMessageDeliveryService::test_create_message_success
```

## Code Review Process

1. **Create Feature Branch**: From `develop` branch
2. **Implement Changes**: Following all specifications and standards
3. **Write Tests**: Ensure all tests pass
4. **Update Documentation**: Update relevant docs and diagrams
5. **Create Pull Request**: Reference spec IDs and ADRs
6. **Code Review**: At least one maintainer must approve
7. **Merge**: After approval and CI checks pass

## Pull Request Guidelines

### PR Title Format

```
[Type] Implement <feature> (Spec #X)
```

Types: `Feature`, `Fix`, `Docs`, `Refactor`, `Test`

### PR Description Template

```markdown
## Description
Brief description of changes.

## References
- Functional Spec (#6), Section X.Y
- State Machines (#7), Section Z
- Resolved TBDs: [list relevant resolved values]

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows Repo & Coding Standards (#17)
- [ ] All spec references included in comments
- [ ] No assumptions outside frozen specs
- [ ] Documentation updated
- [ ] No sensitive data in code or comments
```

## Prohibited Practices

**Do NOT:**
- Invent features not in specifications
- Add assumptions or "convenience" features
- Modify cryptographic parameters
- Add undocumented data fields
- Cache sensitive state beyond defined lifetimes
- Log message content or cryptographic material
- Use security-themed language in UI/copy
- Bypass platform security features

See Non-Goals & Prohibited Behaviors (#2) and Do Not Invent List (#5) for complete details.

## Documentation

### Inline Documentation

- All functions must have docstrings
- Reference relevant spec IDs in docstrings
- No sensitive content in comments

### Diagram Updates

- Use Mermaid syntax for diagrams
- Update diagrams when state machines change
- Include diagrams in `docs/` directory

## Questions or Issues

If you encounter:
- Undefined behavior in specs
- Ambiguous requirements
- Conflicts between specifications
- Questions about implementation

**STOP and ask for clarification.** Do not make assumptions.

## Getting Help

- Review frozen specifications in `specs/` directory
- Check existing code for examples of spec references
- Review ADRs (#16) for architectural decisions
- Contact maintainers for clarification

## Thank You

Thank you for contributing to Abiqua Asset Management. Your adherence to specifications and standards ensures the system remains deterministic, secure, and compliant.
