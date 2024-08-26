from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuration (These should ideally be stored in environment variables for security)
tenant_id = 'bf43acc3-0f1b-43ac-9003-d3a80361852b'  # Azure AD tenant ID
client_id = 'b7fa04c4-21ca-430a-8421-d1a4a376b7d1'  # Azure AD app client ID
client_secret = '1Eg8Q~BuzoHPsBJqfk-cXv6WiDwEwjFz0eYXXa.G'  # Azure AD app client secret
resource = 'https://graph.microsoft.com'  # Azure Graph resource
site_url = '26f5v4.sharepoint.com'  # Fixed SharePoint site URL

# Obtain OAuth token
def get_oauth_token():
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/token'
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource
    }

    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()

    if token_response.status_code != 200:
        return {'error': 'Error obtaining OAuth token', 'description': token_json.get('error_description', 'Unknown error')}, 400

    return token_json.get('access_token')

# Retrieve file permissions
def get_file_permissions(token, file_name):
    headers = {
        'Authorization': f'Bearer {token}'
    }

    file_url = f"{resource}/v1.0/sites/{site_url},c89a5dc9-6128-4101-8cf0-5a2ec307ec00,20454cb4-a004-4cc6-a302-418724c77932/drive/root:/{file_name}:/permissions"
    response = requests.get(file_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data.get('value', [])
    else:
        return handle_errors(response)

# Error handling
def handle_errors(response):
    error_map = {
        401: 'Unauthorized. Check your OAuth token and permissions.',
        403: 'Forbidden. Check your permissions and authentication.',
        400: 'Bad Request. Check the request URL and headers.'
    }
    return {
        'error': error_map.get(response.status_code, 'Error fetching file permissions'),
        'description': response.text
    }, response.status_code

# Extract user permissions
def extract_file_users(permissions):
    file_users = []

    for permission in permissions:
        granted_to = permission.get('grantedTo', {})
        display_name = granted_to.get('user', {}).get('displayName', '')
        if not display_name:
            granted_to_v2 = permission.get('grantedToV2', {})
            display_name = granted_to_v2.get('siteGroup', {}).get('displayName', '')

        if display_name:
            file_users.append(display_name)

    return file_users

@app.route('/get-file-permissions', methods=['POST'])
def get_permissions():
    try:
        data = request.json
        file_name = data.get('file_name')

        if not file_name:
            return jsonify({"error": "Missing required parameter 'file_name'"}), 400

        # Get OAuth token
        token = get_oauth_token()
        if isinstance(token, dict) and 'error' in token:
            return jsonify(token), 400

        # Get file permissions
        permissions = get_file_permissions(token, file_name)
        if isinstance(permissions, tuple):
            return jsonify(permissions[0]), permissions[1]

        file_users = extract_file_users(permissions)

        # Prepare and return the output as JSON
        output = {
            "File users": ', '.join(file_users)
        }
        return jsonify(output), 200

    except Exception as e:
        return jsonify({"error": "Internal server error", "description": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
