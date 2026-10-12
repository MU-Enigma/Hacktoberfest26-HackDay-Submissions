# Test Credentials

## Admin
- Email: richa.kshama@gmail.com
- Password: Back2U@Admin26
- Role: admin

## Demo students (password: Demo@1234; also one-click "demo login" on /login)
- alice@campus.edu (owns lost "White wireless earbuds case", found "Green steel water bottle", lost "Black backpack")
- bob@campus.edu (owns found "Earbuds in white charging case" — private clues: "blue star sticker inside lid, chip on left earbud"; lost "Bunch of keys")
- carol@campus.edu (owns found "Brown leather wallet", lost "Casio calculator")

## Auth endpoints
- POST /api/auth/register {name,email,password,accept_policy,policy_version:"1.0"}
- POST /api/auth/login {email,password} -> {user, token}  (Bearer token or httpOnly cookie)
- POST /api/auth/demo-login {email} (demo students only)
- GET /api/auth/me, POST /api/auth/logout
