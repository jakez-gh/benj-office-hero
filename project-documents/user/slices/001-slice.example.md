# 001‑slice.example (authentication slice)

*This is an example of a "slice design" file; Erik Corkran’s
methodology uses one of these per vertical feature.*

## Slice name

User authentication & session management

## Description

Users must be able to sign up, log in, and maintain an authenticated
session.  This slice provides the backend endpoints and will integrate
with the frontend login UI.

## Inputs

- `POST /signup` request with email/password
- `POST /login` with credentials

## Outputs

- `201 Created` user record
- `200 OK` with JWT token

## Interfaces

- Database table `users` with fields `id`, `email`, `password_hash`.
- JWT signing service using HS256 and a secret stored in
  environment variable.

## Dependencies

- Sending confirmation emails via SendGrid (phase‑later)
- `bcrypt` library for password hashing

## Success Criteria

- New users can register and immediately log in.
- Tokens must be valid for 24 hours and revocable via a logout
  endpoint.

## Edge Cases / Notes

- Rate‑limit login attempts to 5 per IP per hour.
- Password reset is not part of this slice.

---

*After you create a real slice you can prompt the AI:*

> "Here’s my slice design; break it into implementable tasks with file
> paths and test ideas."
