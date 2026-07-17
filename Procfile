release: python AuditPro/manage.py migrate --noinput && python AuditPro/manage.py collectstatic --noinput
web: gunicorn work7.wsgi --chdir AuditPro --bind 0.0.0.0:$PORT --log-file -
