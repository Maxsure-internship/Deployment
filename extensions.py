from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
import os

mailer = Mail()
serializer = URLSafeTimedSerializer(os.environ.get("SESSION_KEY", ""))