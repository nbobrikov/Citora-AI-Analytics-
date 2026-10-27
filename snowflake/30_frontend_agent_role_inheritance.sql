-- Allow the role used by the frontend connection to invoke Cortex Agent.
-- The service user already has CITORA_FRONTEND_UPLOADER directly; inheriting
-- CITORA_FRONTEND_READER keeps analytics and Agent permissions read-only.

USE ROLE SECURITYADMIN;

GRANT ROLE CITORA_FRONTEND_READER
    TO ROLE CITORA_FRONTEND_UPLOADER;

SHOW GRANTS TO ROLE CITORA_FRONTEND_UPLOADER;
