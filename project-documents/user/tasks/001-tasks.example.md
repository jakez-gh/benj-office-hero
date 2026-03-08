# 001‑tasks.example (authentication tasks)

*Generated from the example slice above; each bullet represents a
concrete work item that an AI agent could implement.*

- Create `src/auth/models.py` with `User` SQLAlchemy model.
- Add `/signup` route in `src/auth/routes.py`:
  - validate email/password
  - hash password with bcrypt
  - insert user row
  - return 201 response
- Write unit tests for signup route (`tests/test_signup.py`).
- Add `/login` route:
  - verify credentials
  - issue JWT token containing `user_id`
  - return 200 response with token
- Implement JWT utility module (`src/auth/jwt_utils.py`) with `encode`
  and `decode` functions; include expiration claim.
- Add middleware to authenticate requests and attach `current_user`.
- Write integration tests ensuring login returns valid token and
  middleware rejects requests without token.
- Document environment variables in `README.md` (`JWT_SECRET`).

*If you run Context Forge, it will produce a similar list when given the
slice design; otherwise you can prompt the AI directly.*
