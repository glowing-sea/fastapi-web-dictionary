# Layered FastAPI Dictionary App (MDX) + Idea Board

Extended app:
- keeps **Idea Board**
- adds **MDX Dictionary** + **Vocabulary** + **History**
- adds **Admin dictionary manager**

## Run

```bash
cd fastapi_dictionary_app
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Admin
All new users are normal users (`users.is_admin = 0`).
To make an admin, update DB manually:

```sql
UPDATE users SET is_admin = 1 WHERE username = 'yourname';
```

Admin can upload a dictionary ZIP (must contain exactly one `.mdx`), optional `.mdd`, `.css`, images, etc.

## MDX assets
The app rewrites relative `src=`/`href=` in MDX HTML to `/dict_asset/<dict_id>/...`
The asset endpoint serves:
1) extracted files from ZIP, else
2) resources inside any `.mdd` (on-demand lookup)
