// Fill these in from the `sam deploy` outputs. None of these values are secrets.
export const config = {
  apiUrl: "https://qw2nhc5g9h.execute-api.us-east-1.amazonaws.com",                 // ApiUrl output, e.g. https://abc123.execute-api.ap-southeast-2.amazonaws.com
  cognitoDomain: "ecoguard-fit3184-bl.auth.us-east-1.amazoncognito.com",          // CognitoDomain output, e.g. ecoguard-team07.auth.ap-southeast-2.amazoncognito.com
  clientId: "1fbnr0rdhs6us3929l7a76j0m9",               // UserPoolClientId output
  redirectUri: window.location.origin + "/", // must match FrontendOrigin in the stack
};
