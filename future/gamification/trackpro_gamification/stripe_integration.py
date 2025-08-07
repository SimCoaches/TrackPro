"""
Stripe Integration for TrackPro Race Pass Premium Purchases
"""

import os
import logging
from typing import Dict, Any, Tuple, Optional
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class StripePaymentProcessor:
    """Handles Stripe payment processing for premium race pass purchases."""
    
    def __init__(self):
        """Initialize Stripe with API keys from environment variables."""
        # Set Stripe API key from environment variable
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        
        # Race Pass pricing
        self.RACE_PASS_PRICE = 999  # $9.99 in cents
        self.CURRENCY = 'usd'
        self.RACE_PASS_PRICE_ID = os.getenv('STRIPE_RACE_PASS_PRICE_ID')  # Monthly subscription price ID
        
        if not stripe.api_key:
            logger.warning("Stripe secret key not found in environment variables. Payment processing will be disabled.")
        
    def create_checkout_session(self, success_url: str, cancel_url: str, 
                               customer_email: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a Stripe Checkout Session for race pass subscription.
        
        Args:
            success_url: URL to redirect to after successful payment
            cancel_url: URL to redirect to if payment is cancelled
            customer_email: Customer email (optional)
            
        Returns:
            Tuple of (success, checkout_session_data)
        """
        try:
            if not stripe.api_key:
                return False, {"error": "Stripe not configured"}
            
            # Create checkout session for monthly subscription
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': self.CURRENCY,
                        'product_data': {
                            'name': 'TrackPro Premium Race Pass',
                            'description': 'Monthly subscription with exclusive rewards and double XP',
                        },
                        'unit_amount': self.RACE_PASS_PRICE,
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'product': 'race_pass_premium',
                    'version': '1.0',
                    'user_email': customer_email or ''
                }
            )
            
            return True, {
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'amount': self.RACE_PASS_PRICE,
                'currency': self.CURRENCY
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {e}")
            return False, {"error": "Payment processing unavailable"}

    def create_payment_intent(self, amount: int = None, currency: str = None, 
                            metadata: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a Stripe Payment Intent for race pass purchase.
        
        Args:
            amount: Amount in cents (default: race pass price)
            currency: Currency code (default: USD)
            metadata: Additional metadata for the payment
            
        Returns:
            Tuple of (success, payment_intent_data)
        """
        try:
            if not stripe.api_key:
                return False, {"error": "Stripe not configured"}
            
            amount = amount or self.RACE_PASS_PRICE
            currency = currency or self.CURRENCY
            metadata = metadata or {}
            
            # Add default metadata
            metadata.update({
                'product': 'race_pass_premium',
                'version': '1.0'
            })
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata,
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            return True, {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount,
                'currency': currency
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {e}")
            return False, {"error": "Payment processing unavailable"}
    
    def confirm_payment(self, payment_intent_id: str, payment_method_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Confirm a payment intent with a payment method.
        
        Args:
            payment_intent_id: The payment intent ID
            payment_method_id: The payment method ID
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            if not stripe.api_key:
                return False, {"error": "Stripe not configured"}
            
            payment_intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )
            
            if payment_intent.status == 'succeeded':
                return True, {
                    'payment_intent_id': payment_intent.id,
                    'status': payment_intent.status,
                    'amount_received': payment_intent.amount_received
                }
            else:
                return False, {
                    'status': payment_intent.status,
                    'error': 'Payment not completed'
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error confirming payment: {e}")
            return False, {"error": "Payment confirmation failed"}
    
    def create_customer(self, email: str, name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a Stripe customer for future payments.
        
        Args:
            email: Customer email
            name: Customer name (optional)
            
        Returns:
            Tuple of (success, customer_data)
        """
        try:
            if not stripe.api_key:
                return False, {"error": "Stripe not configured"}
            
            customer_data = {'email': email}
            if name:
                customer_data['name'] = name
            
            customer = stripe.Customer.create(**customer_data)
            
            return True, {
                'customer_id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {e}")
            return False, {"error": "Customer creation failed"}
    
    def retrieve_payment_intent(self, payment_intent_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Retrieve a payment intent by ID.
        
        Args:
            payment_intent_id: The payment intent ID
            
        Returns:
            Tuple of (success, payment_intent_data)
        """
        try:
            if not stripe.api_key:
                return False, {"error": "Stripe not configured"}
            
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return True, {
                'id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'metadata': payment_intent.metadata
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error retrieving payment intent: {e}")
            return False, {"error": "Payment retrieval failed"}
    
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(stripe.api_key and self.publishable_key)
    
    def get_publishable_key(self) -> Optional[str]:
        """Get the Stripe publishable key for client-side use."""
        return self.publishable_key

# Global instance
stripe_processor = StripePaymentProcessor()

def create_race_pass_checkout(user_email: str = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Create a Stripe Checkout session for race pass subscription.
    
    Args:
        user_email: User's email address (optional)
        
    Returns:
        Tuple of (success, checkout_data)
    """
    try:
        # Define success and cancel URLs (these would be your app's URLs)
        success_url = "https://trackpro.app/race-pass/success"  # Replace with your actual URL
        cancel_url = "https://trackpro.app/race-pass/cancel"    # Replace with your actual URL
        
        success, checkout_data = stripe_processor.create_checkout_session(
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user_email
        )
        
        return success, checkout_data
        
    except Exception as e:
        logger.error(f"Error creating race pass checkout: {e}")
        return False, {"error": "Checkout creation failed"}

def process_race_pass_payment(user_email: str, user_name: str = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to process a race pass payment.
    
    Args:
        user_email: User's email address
        user_name: User's name (optional)
        
    Returns:
        Tuple of (success, payment_data)
    """
    try:
        # Create customer if needed
        customer_success, customer_data = stripe_processor.create_customer(user_email, user_name)
        
        if not customer_success:
            logger.warning(f"Could not create customer: {customer_data}")
        
        # Create payment intent
        metadata = {
            'user_email': user_email,
            'product_type': 'race_pass_premium'
        }
        
        if customer_success:
            metadata['customer_id'] = customer_data['customer_id']
        
        success, payment_data = stripe_processor.create_payment_intent(metadata=metadata)
        
        if success and customer_success:
            payment_data['customer_id'] = customer_data['customer_id']
        
        return success, payment_data
        
    except Exception as e:
        logger.error(f"Error processing race pass payment: {e}")
        return False, {"error": "Payment processing failed"}

def validate_payment_completion(payment_intent_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that a payment was completed successfully.
    
    Args:
        payment_intent_id: The payment intent ID to validate
        
    Returns:
        Tuple of (success, validation_data)
    """
    success, payment_data = stripe_processor.retrieve_payment_intent(payment_intent_id)
    
    if success and payment_data.get('status') == 'succeeded':
        return True, {
            'validated': True,
            'amount': payment_data['amount'],
            'currency': payment_data['currency'],
            'metadata': payment_data.get('metadata', {})
        }
    
    return False, {
        'validated': False,
        'error': payment_data.get('error', 'Payment not completed')
    } 