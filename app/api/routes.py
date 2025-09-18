"""
API Routes

This module contains the API route definitions.
"""

from flask import jsonify, request
from marshmallow import Schema, fields, validate

from app.utils.decorators import rate_limit, require_auth, require_role, validate_json
from .. import api_bp

# Example schema for request validation
class ProductSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(required=False, allow_none=True)
    price = fields.Float(required=True, validate=validate.Range(min=0.01))
    stock = fields.Int(required=True, validate=validate.Range(min=0))


@api_bp.route('/public/hello', methods=['GET'])
@rate_limit(category='public')
def public_hello():
    """Public endpoint with rate limiting."""
    return jsonify({
        'message': 'Hello, world!',
        'status': 'success'
    })


@api_bp.route('/auth/me', methods=['GET'])
@require_auth
@rate_limit(category='api', subcategory='authenticated')
def get_current_user():
    """Get current user information (requires authentication)."""
    return jsonify({
        'id': request.user.uid,
        'email': request.user.email,
        'roles': getattr(request.user, 'roles', [])
    })


@api_bp.route('/products', methods=['POST'])
@require_auth
@require_role('seller')
@rate_limit(limit=10, per=60)  # 10 requests per minute
@validate_json(ProductSchema)
def create_product():
    """Create a new product (requires seller role)."""
    # The validated data is available in request.validated_data
    product_data = request.validated_data
    
    # In a real application, you would save the product to the database here
    # product = Product.create(**product_data)
    
    return jsonify({
        'status': 'success',
        'message': 'Product created successfully',
        'data': product_data
    }), 201


@api_bp.route('/search', methods=['GET'])
@rate_limit(category='search')
def search():
    """Search endpoint with rate limiting."""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'status': 'error',
            'message': 'Search query is required',
            'code': 'missing_query_parameter'
        }), 400
    
    # In a real application, you would perform the search here
    results = [
        {'id': 1, 'name': f'Result for {query} 1'},
        {'id': 2, 'name': f'Result for {query} 2'},
    ]
    
    return jsonify({
        'status': 'success',
        'query': query,
        'results': results,
        'total': len(results)
    })


@api_bp.route('/admin/stats', methods=['GET'])
@require_auth
@require_role('admin')
@rate_limit(category='admin')
def admin_stats():
    """Admin statistics endpoint (requires admin role)."""
    # In a real application, you would fetch actual statistics
    return jsonify({
        'status': 'success',
        'stats': {
            'users': 1000,
            'products': 5000,
            'orders': 2500,
            'revenue': 100000.00
        }
    })
