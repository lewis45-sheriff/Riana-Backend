# Android SIM gateway setup

This integration uses SMSGate for Android in Cloud Server mode. Invitations
are sent by the phone's SIM; users reply to that normal phone number with three
ratings (for example `4 5 4`). It does not run a one-question-at-a-time survey.

1. Install the Android application from https://docs.sms-gate.app/installation/.
   Use a dedicated SIM with SMS service and keep the phone powered and online.
2. Enable Cloud Server mode and start its service. Copy its generated username
   and password. Select the intended SIM in the app if the phone has multiple SIMs.
3. In Settings → Webhooks → Signing Key, configure a random key of at least
   32 characters. The backend must use that exact same key. Enable incoming SMS
   permissions and allow the app to keep running in the background.
4. On EC2, edit `/home/ubuntu/apps/backend/.env` (never commit it):

   ```dotenv
   SMS_PROVIDER=smsgate
   SMSGATE_USERNAME=your_phone_cloud_username
   SMSGATE_PASSWORD=your_phone_cloud_password
   SMSGATE_WEBHOOK_SECRET=the_same_signing_key_from_the_phone
   SMSGATE_DEVICE_ID=your_device_id
   ```

   `SMSGATE_DEVICE_ID` is optional for a single-device account; specify it when
   selecting a particular device. The cloud base URL defaults to
   `https://api.sms-gate.app/3rdparty/v1`.
5. Register the callback and restart Django:

   ```bash
   cd /home/ubuntu/apps/backend
   .venv/bin/python manage.py register_sms_gateway
   sudo systemctl restart riana-backend
   ```

6. Confirm `sms:received` is registered in the app, then send one invitation
   from Dashboard → SMS surveys. A queued result is not confirmation of delivery;
   check the phone's outgoing queue. Reply from a second phone with `4 5 4`.
   Confirm the response appears on the dashboard with source `sms`.

The default callback is `https://34.207.109.162/api/sms/gateway/inbound`, using
the server's trusted IP certificate to bypass Cloudflare browser challenges.
You can register the domain URL using `--url
https://smartedu.co.ke/api/sms/gateway/inbound` once Cloudflare allows this path
without browser challenges. Webhooks use `X-Timestamp` and `X-Signature`,
verified with HMAC-SHA256 over the raw body followed by the timestamp. Requests
outside five minutes are rejected; keep the phone clock automatic. Database
deduplication uses device ID and event ID. Only invited phone numbers are
processed, and unrelated/invalid SMS is ignored without creating feedback.

Phone-side credentials are different from Africa's Talking credentials.
The existing provider remains active until `SMS_PROVIDER=smsgate` is set.
No automatic fallback to a paid provider occurs when the gateway is offline.
Switch back with `SMS_PROVIDER=africastalking` and restart the backend if needed.
Do not expose phone credentials or the signing key in Swagger or frontend code.

The app provider's cloud service processes message data. Review its privacy
terms and your mobile operator's messaging terms before production use.

Official references:
- https://docs.sms-gate.app/getting-started/public-cloud-server/
- https://docs.sms-gate.app/features/webhooks/
