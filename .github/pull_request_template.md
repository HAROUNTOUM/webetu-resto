## Summary

<!-- What changed and why? Link the issue. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / tests / CI
- [ ] API compatibility update

## Verification

<!-- Paste the commands you actually ran, without credentials or tokens. -->

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov
```

## Checklist

- [ ] No real credentials, JWTs, tokens, APKs or decompiled bundles in the diff.
- [ ] Tests cover the new behaviour; existing tests still pass.
- [ ] Documentation updated if the API, CLI or configuration changed.
- [ ] The change respects the 24 h rule, the D+1..D+3 window and the chosen restaurant.
