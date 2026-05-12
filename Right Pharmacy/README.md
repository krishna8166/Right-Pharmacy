# QuickMart — Web App

## Run locally (on your PC / same network)

```bash
pip install flask
python app.py
```

- **Customer portal** → http://localhost:5000  
  Share this URL with anyone on the same Wi-Fi network using your PC's local IP, e.g. `http://192.168.1.10:5000`

- **Admin dashboard** → http://localhost:5000/admin  
  Password: `admin123`

---

## Deploy FREE online (Render.com — recommended)

1. Push this folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app`
   - **Environment vars**:
     - `SECRET_KEY` = any long random string
     - `ADMIN_PASSWORD` = your chosen password
5. Click Deploy — you'll get a public URL like `https://quickmart-xyz.onrender.com`

Share the public URL with your customers. Admin dashboard is at `/admin`.

---

## Deploy FREE online (Railway.app)

1. Push to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add env vars: `SECRET_KEY`, `ADMIN_PASSWORD`
4. Railway auto-detects the Procfile and deploys

---

## Environment variables

| Variable         | Default          | Description                        |
|------------------|------------------|------------------------------------|
| `SECRET_KEY`     | dev key          | Flask session secret (change this!)|
| `ADMIN_PASSWORD` | `admin123`       | Admin login password               |
| `PORT`           | `5000`           | Port to listen on                  |
| `DB_PATH`        | `retail_shop.db` | SQLite database file path          |

---

## How it works

- Customer visits the URL → browses catalog → adds to cart → places order (no payment)
- Admin visits `/admin` → sees live pending orders (auto-refreshes every 10 seconds)
- Admin marks orders delivered → stock reduces automatically → sale is logged
- Both sides read/write the **same SQLite database** in real time
