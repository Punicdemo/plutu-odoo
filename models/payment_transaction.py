# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    plutu_mobile_number = fields.Char(
        string="Mobile Number",
        help="Customer's mobile number for Plutu/T-Lync payment."
    )
    plutu_birth_year = fields.Char(
        string="Birth Year",
        help="Customer's birth year for Sadad payment."
    )
    plutu_process_id = fields.Char(
        string="Process ID",
        readonly=True,
        help="Process ID returned by Sadad API after sending OTP."
    )
    otp_code = fields.Char(
        string="OTP Code",
        help="One-Time Password sent to the customer's phone."
    )

    def _format_plutu_mobile_number(self, raw_number):
        """Format mobile number for Plutu (Libyan format: 09XXXXXXXX)."""
        if not raw_number:
            return None

        cleaned = re.sub(r'\D', '', raw_number)

        if cleaned.startswith('218'):
            cleaned = cleaned[3:]

        if not cleaned.startswith('0'):
            cleaned = '0' + cleaned

        if len(cleaned) != 10 or not cleaned.startswith('09'):
            raise ValidationError(_(
                "Invalid mobile number format for Plutu: '%s'. "
                "Please use a valid Libyan mobile number (e.g., 0912345678 or +218912345678)."
            ) % raw_number)

        return cleaned

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'plutu':
            return res

        _logger.info("Payment Method Name: %s", self.payment_method_id.name)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        invoice = self.invoice_ids[:1]

        if invoice and invoice.partner_id:
            raw_mobile = self.plutu_mobile_number or invoice.partner_id.phone or invoice.partner_id.mobile
        else:
            raw_mobile = self.plutu_mobile_number or self.partner_id.phone or self.partner_id.mobile

        if not raw_mobile:
            raise ValidationError(_("A valid mobile number is required to process this payment."))

        formatted_mobile = self._format_plutu_mobile_number(raw_mobile)

        payload = {
            'amount': str(self.amount),
            'invoice_no': self.reference,
            'return_url': base_url + '/payment/plutu/return',
            'mobile_number': formatted_mobile,
            'callback_url': base_url + '/payment/plutu/webhook',
            'lang': 'en',
        }

        payment_link_data = self.provider_id._plutu_make_request(
            f'transaction/{self.payment_method_id.code}/confirm', payload=payload
        )
        return {'api_url': payment_link_data['result']['redirect_url']}

    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from Plutu's payment data."""
        if provider_code != 'plutu':
            return super()._extract_reference(provider_code, payment_data)

        reference = payment_data.get('invoice_no')
        if not reference:
            raise ValidationError("Plutu: " + _("Received data with missing reference."))
        return reference

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount from Plutu's payment data."""
        if self.provider_code != 'plutu':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': float(payment_data.get('amount', 0.0)),
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on Plutu's payment data."""
        if self.provider_code != 'plutu':
            return super()._apply_updates(payment_data)

        if payment_data.get('gateway') in ('localbankcards', 'tlync'):
            if payment_data.get('approved'):
                self._set_done()
                _logger.info("Plutu: Payment approved for transaction %s.", self.reference)
            elif payment_data.get('canceled'):
                self._set_canceled()
                _logger.info("Plutu: Payment canceled for transaction %s.", self.reference)
            else:
                self._set_pending()
        else:
            self._set_pending()
