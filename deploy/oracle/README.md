# Oracle Always Free Deployment

This is the no-sleep deployment path for the NFL PBP Predictor resume site.
It runs the existing Django, React, SQLite, and scikit-learn app on an Oracle Cloud Always Free VM with Docker Compose.

## Why This Option

Render Free is easier, but it sleeps after inactivity. For a recruiter-facing resume project, the first impression matters, so the best free no-sleep option is an always-on VM.

Oracle Cloud Always Free is a good fit because this project is a normal server app:

- Django + Gunicorn backend
- React bundle built by Webpack
- SQLite demo database
- checked-in scikit-learn `.joblib` model artifacts

## One-Time Oracle Setup

1. Create an Oracle Cloud Always Free account.
2. Create an Always Free compute instance.
   - Recommended: Ampere A1, Ubuntu, 1 OCPU, 2-4 GB RAM.
   - If A1 capacity is unavailable, try another availability domain or region.
3. Add ingress rules for:
   - TCP `22` from your IP for SSH
   - TCP `80` from `0.0.0.0/0`
   - TCP `443` from `0.0.0.0/0`
4. SSH into the VM.

## Server Setup

Install Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and SSH back in so your Docker group membership applies.

## Deploy The App

Clone the repository:

```bash
git clone https://github.com/Sam55wats/NflPbpPredictor.git
cd NflPbpPredictor
git checkout nflpredictor/render-free-deploy
```

Create `.env`:

```bash
openssl rand -base64 48
nano .env
```

Use this template:

```bash
SECRET_KEY=paste-the-generated-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SITE_ADDRESS=your-domain.com
WEB_CONCURRENCY=2
```

`WEB_CONCURRENCY=2` is reasonable for the recommended Oracle VM because it has
more memory than the Northflank free container. If you deploy to a smaller
instance, start with `WEB_CONCURRENCY=1` and increase only after checking memory
usage during prediction requests.

If you are testing with only the VM public IP, use this instead:

```bash
ALLOWED_HOSTS=your-public-ip
SITE_ADDRESS=:80
```

Start the site:

```bash
docker compose -f docker-compose.oracle.yml up -d --build
```

Check it:

```bash
docker compose -f docker-compose.oracle.yml ps
docker compose -f docker-compose.oracle.yml logs -f web
```

## Updating Later

```bash
git pull
docker compose -f docker-compose.oracle.yml up -d --build
```

## Notes

- Caddy automatically provisions HTTPS when `SITE_ADDRESS` is a real domain pointed at the VM.
- The app keeps running unless the VM is stopped or reclaimed.
- Oracle may reclaim idle Always Free instances, so keep the app genuinely available and monitor it occasionally.
