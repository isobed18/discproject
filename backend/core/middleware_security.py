from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HSTS (Strict-Transport-Security) - Enforce HTTPS for 1 year
        # In a real scenario, this header essentially tells the browser to NEVER
        # try http:// again. Only generally added when on HTTPS. 
        # For local dev (http://localhost), browsers often ignore this or it causes issues 
        # if you don't actually have TLS. We set it but might need conditional logic for prod.
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Prevent MIME-Sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (modern browsers use CSP, but this is legacy support)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP (Content Security Policy) - Very strict for API
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
        return response
