# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import logging
import pprint
from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class PaylinkController(http.Controller):
    _return_url = '/payment/plutu/return'
    _webhook_url = '/payment/plutu/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def plutu_return_from_payment(self, **data):
        _logger.info("Handling redirection from Plutu with data:\n%s", pprint.pformat(data))

        plutu_provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'plutu')], limit=1
        )
        plutu_secret_key = plutu_provider.plutu_secret_key
        self._verify_plutu_callback_hash(data, plutu_secret_key)

        request.env['payment.transaction'].sudo()._process('plutu', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def plutu_payment_webhook(self):
        data = request.get_json_data()
        _logger.info("Notification received from Plutu with data:\n%s", pprint.pformat(data))

        plutu_provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'plutu')], limit=1
        )
        plutu_secret_key = plutu_provider.plutu_secret_key
        self._verify_plutu_callback_hash(data, plutu_secret_key, 'callback')

        request.env['payment.transaction'].sudo()._process('plutu', data)
        return request.make_json_response('')

    @staticmethod
    def _verify_plutu_callback_hash(parameters, secret_key, key='return'):
        if not secret_key or not secret_key.strip():
            raise Exception('Secret key is not configured')

        if key == 'callback':
            callback_parameters = [
                'gateway', 'approved', 'amount', 'invoice_no', 'canceled',
                'payment_method', 'transaction_id',
            ]
        else:
            callback_parameters = [
                'gateway', 'approved', 'canceled', 'invoice_no', 'amount', 'transaction_id',
            ]

        data = '&'.join(
            f"{param}={parameters[param]}" for param in callback_parameters if param in parameters
        )

        hash_from_callback = parameters.get('hashed')
        if not hash_from_callback:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        hash_from_callback = hash_from_callback.upper()
        generated_hash = hmac.new(
            secret_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256
        ).hexdigest().upper()

        if not hmac.compare_digest(generated_hash, hash_from_callback):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
