export const config = {
  apiUrl: "https://0hi6iur5ud.execute-api.us-east-1.amazonaws.com",                // ApiUrl output, e.g. https://abc123.execute-api.ap-southeast-2.amazonaws.com
  cognitoDomain: "ecoguard-fit3184-team95.auth.us-east-1.amazoncognito.com",          // CognitoDomain output, e.g. ecoguard-team07.auth.ap-southeast-2.amazoncognito.com
  clientId: "uh4l151r1ijt5c1o1uos1cpur",               // UserPoolClientId output
  redirectUri: window.location.origin + "/", // must match FrontendOrigin in the stack
};