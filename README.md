# Artisan AI

A platform connecting artisans with customers using AI-powered tools.

## Project Overview

Artisan AI is a full-stack e-commerce platform that connects Indian artisans with global buyers. The platform provides artisans with AI-powered tools to enhance their product listings, pricing, and marketing efforts, while offering buyers a seamless shopping experience with personalized recommendations.

## Features

### For Artisans
- **AI-Powered Product Listings**: Generate compelling product descriptions and titles using AI
- **Smart Pricing**: Get AI-powered pricing recommendations based on market trends
- **Inventory Management**: Track and manage product inventory
- **Order Fulfillment**: Process and track customer orders
- **Analytics Dashboard**: View sales performance and customer insights
- **Verification System**: Get verified as an authentic artisan

### For Buyers
- **Marketplace**: Browse and search for unique handmade products
- **Personalized Recommendations**: Discover products based on your preferences
- **Secure Checkout**: Multiple payment options with secure processing
- **Order Tracking**: Real-time order status updates
- **Wishlists & Favorites**: Save items for later

### AI Tools
- **Product Description Generator**: Create engaging product descriptions
- **Image Enhancement**: Improve product photos with AI
- **Pricing Assistant**: Get optimal pricing suggestions
- **Trend Analysis**: Stay updated with market trends
- **Social Media Content**: Generate posts for social media promotion
  - Brand kit creation
  - Market trend analysis
  - Pricing recommendations
  - Social media content generation
- **Secure Authentication**: Email/Password and Phone (OTP) login
- **E-commerce Marketplace**:
  - Product listings with rich media
  - Shopping cart and checkout
  - Order management
- **Artisan Dashboard**:
  - Product management
  - Sales analytics
  - Customer insights

## Tech Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Database**: Firebase Firestore
- **Authentication**: Firebase Authentication
- **Storage**: Firebase Storage
- **AI/ML**: Google Gemini API
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+ (for frontend assets)
- Firebase account
- Google Cloud account (for Google AI and Maps APIs)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/artisan-ai.git
   cd artisan-ai
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration
   - Add your Firebase service account key as `firebase-service-account-key.json`

5. Run the development server:
   ```bash
   flask run
   ```

## Project Structure

```
artisan-ai/
├── app/                    # Application package
│   ├── auth/               # Authentication routes and logic
│   ├── artisan/            # Artisan-specific routes and logic
│   ├── buyer/              # Buyer-specific routes and logic
│   ├── admin/              # Admin routes and logic
│   ├── api/                # API endpoints
│   ├── static/             # Static files (CSS, JS, images)
│   ├── templates/          # HTML templates
│   ├── __init__.py         # Application factory
│   └── config.py           # Configuration settings
├── scripts/                # Utility scripts
├── tests/                  # Test files
├── .env                    # Environment variables (ignored by git)
├── .gitignore              # Git ignore file
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Security

- All sensitive data is stored in environment variables
- CSRF protection is enabled for all forms
- Password hashing with Firebase Authentication
- Input validation on all user inputs
- Rate limiting on authentication endpoints

## Deployment

1. Set up a new project on Vercel
2. Connect your GitHub repository
3. Add environment variables in Vercel project settings
4. Deploy!

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter) - email@example.com

Project Link: [https://github.com/yourusername/artisan-ai](https://github.com/yourusername/artisan-ai)
