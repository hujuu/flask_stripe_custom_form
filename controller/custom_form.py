"""Functions related to registration of Stripe Connect Custom."""
import os
from functools import wraps
from google.cloud import firestore
from flask import request, abort, Blueprint
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
import stripe

db = firestore.Client(project='')
app = Blueprint("custom_form", __name__)
stripe.api_key = os.environ['stripe_api_key']


def requires_auth(func):
    """Users who are not logged in are redirected to the top page."""

    @wraps(func)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/')
        return func(*args, **kwargs)

    return decorated


@app.route('/custom_form')
@requires_auth
def custom_form():
    """
    The page to start account registration.
    """
    affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
    doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
    doc = doc_ref.get()
    stripe_acct_id = doc.to_dict().get('stripe_acct_id', None)
    response = stripe.Account.retrieve(stripe_acct_id)
    if stripe_acct_id:
        return redirect(url_for('custom_form.show_stripe_acct'))

    return render_template(
        'custom_form/index.html',
        doc=doc,
        acct=response
    )


@app.route('/custom_form/new', methods=['POST'])
@requires_auth
def registration_stripe():
    """Get the stripe registration form."""
    response = stripe.Account.create(
        country="JP",
        type="custom",
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
            "jcb_payments": {"requested": True},
        },
        business_profile={
            "product_description": "",
        }
    )
    response_link = stripe.AccountLink.create(
        account=response['id'],
        refresh_url="https://xxxx.a.run.app/custom_form/detail",
        return_url="https://xxxx.a.run.app/custom_form/detail",
        type="account_onboarding",
        collect="eventually_due",
    )

    affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
    doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
    doc_ref.update(
        {
            'stripe_acct_id': response['id'],
        }
    )

    return redirect(response_link['url'])


@app.route('/custom_form/edit', methods=['GET', 'POST'])
@requires_auth
def edit_stripe_acct():
    """Additions and changes of optional items."""
    try:
        affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
        doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
        doc = doc_ref.get()
        stripe_acct_id = doc.to_dict().get('stripe_acct_id', None)
        response = stripe.Account.retrieve(stripe_acct_id)
        if len(response['requirements']['eventually_due']) > 0:
            status = response['requirements']['eventually_due'][0]
        else:
            status = 'complete'

        if request.method == 'GET':
            if not stripe_acct_id:
                return jsonify({'error': 'Could not find connect account.'}), 404

            return render_template(
                'custom_form/edit.html',
                acct=response,
                status=status
            )
        if request.method == 'POST':
            statement_descriptor = request.form['statement_descriptor']
            statement_descriptor_kana = request.form['statement_descriptor_kana']
            statement_descriptor_kanji = request.form['statement_descriptor_kanji']
            url = request.form['url']

            stripe.Account.modify(
                stripe_acct_id,
                settings={
                    "payments": {
                        "statement_descriptor": statement_descriptor,
                        "statement_descriptor_kana": statement_descriptor_kana,
                        "statement_descriptor_kanji": statement_descriptor_kanji
                    },
                    "payouts": {
                        "schedule": {
                            "interval": "manual",
                        },
                    },
                },
                business_profile={"url": url,
                                  "product_description": ""},
            )

            return redirect(url_for('custom_form.show_stripe_acct'))
        return abort(400)
    except (Exception,):
        return str(Exception)


@app.route('/custom_form/detail', methods=['GET'])
@requires_auth
def show_stripe_acct():
    """Show registered account information."""
    try:
        affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
        doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
        doc = doc_ref.get()
        stripe_acct_id = doc.to_dict().get('stripe_acct_id', None)

        if not stripe_acct_id:
            return jsonify({'error': 'Could not find Connect account.'}), 404

        response = stripe.Account.retrieve(stripe_acct_id)
        if len(response['requirements']['eventually_due']) > 0:
            status = response['requirements']['eventually_due'][0]
        else:
            status = 'complete'

        return render_template(
            'custom_form/show.html',
            acct=response,
            status=status
        )

    except Exception as e:
        return str(e)


@app.route('/custom_form/add_bank', methods=['GET', 'POST'])
@requires_auth
def create_external_account_stripe_acct():
    """Add a bank account."""
    try:
        affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
        doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
        doc = doc_ref.get()
        stripe_acct_id = doc.to_dict().get('stripe_acct_id', None)
        response = stripe.Account.retrieve(stripe_acct_id)
        if len(response['requirements']['eventually_due']) > 0:
            status = response['requirements']['eventually_due'][0]
        else:
            status = 'complete'

        if request.method == 'GET':
            if not stripe_acct_id:
                return jsonify({'error': 'Could not find connect account.'}), 404

            return render_template(
                'custom_form/create_external_account.html',
                acct=response,
                status=status,
            )
        if request.method == 'POST':
            account_holder_name = request.form['account_holder_name']
            routing_number = request.form['routing_number']
            account_number = request.form['account_number']

            response_token = stripe.Token.create(
                bank_account={
                    "country": "JP",
                    "currency": "jpy",
                    "account_holder_name": account_holder_name,
                    "account_holder_type": response['business_type'],
                    "routing_number": routing_number,
                    "account_number": account_number,
                },
            )
            response = stripe.Account.create_external_account(
                stripe_acct_id,
                external_account=response_token['id']
            )
            return redirect(url_for('custom_form.show_stripe_acct'))

        return abort(400)
    except Exception as e:
        return str(e)


@app.route('/custom_form/restart', methods=['POST'])
@requires_auth
def restart_stripe():
    """Resuming Account registration on Stripe's form."""
    affiliated_tenant = session['jwt_payload'].get('https://xxxx/app_metadata', None)
    doc_ref = db.collection('tenants').document(affiliated_tenant['tenant'])
    doc = doc_ref.get()
    stripe_acct_id = doc.to_dict().get('stripe_acct_id', None)

    response_link = stripe.AccountLink.create(
        account=stripe_acct_id,
        refresh_url="https://xxxx.a.run.app/custom_form/detail",
        return_url="https://xxxx.a.run.app/custom_form/detail",
        type="account_onboarding",
        collect="eventually_due",
    )

    return redirect(response_link['url'])
