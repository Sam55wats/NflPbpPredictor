# Northflank Deployment

This is the recommended no-sleep deployment path for the recruiter-facing NFL PBP Predictor demo.

Northflank fits this app because it can build the repository Dockerfile and run the existing Django, React, SQLite, and scikit-learn setup without a platform rewrite.

## Repository Settings

- Repository: `Sam55wats/NflPbpPredictor`
- Branch: `nflpredictor/render-free-deploy`
- Build type: `Dockerfile`
- Dockerfile path: `Dockerfile`
- Build context: repository root
- Runtime port: `8000`
- Protocol: `HTTP`
- Public port: enabled
- Health check: HTTP `GET /healthz/` on port `8000`

Northflank injects `NF_HOSTS` with the generated service hostnames. The Django settings now add those values to `ALLOWED_HOSTS`, so the generated `*.code.run` URL should work without manually copying it into Django settings.

## Runtime Variables

Set these on the Northflank service:

```bash
DEBUG=False
SECRET_KEY=<generate-a-new-secret>
WEB_CONCURRENCY=2
```

Optional:

```bash
ALLOWED_HOSTS=<custom-domain-or-extra-hosts>
```

Leave `ALLOWED_HOSTS` empty for the generated Northflank URL unless a custom domain is added.

Generate a secret locally with:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Dashboard Steps

1. Create or open a Northflank project.
2. Connect GitHub if it is not connected yet.
3. Create a combined service or a build service plus deployment service.
4. Select `Sam55wats/NflPbpPredictor`.
5. Select branch `nflpredictor/render-free-deploy`.
6. Choose Dockerfile build.
7. Expose port `8000` as public HTTP.
8. Add runtime variables from the section above.
9. Add a HTTP health check for `/healthz/`.
10. Deploy.

After deployment, open the generated `*.code.run` URL and test:

- `/`
- `/api/season/`
- `/healthz/`

## Expected Behavior

The first page should load without Render-style sleeping. If the app starts but the page is blank, inspect the browser console and verify `/static/index-bundle.js` is returned as JavaScript. The project now builds `index-bundle.js` instead of `index-bundle.jsx` to avoid strict MIME blocking.
