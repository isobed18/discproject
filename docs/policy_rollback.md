# Policy Rollback Strategy

## Overview
In the event of a bad policy deployment (OPA Rego files) that blocks legitimate traffic or opens security holes, we must revert to a known good state immediately.

## "Break Glass" Procedure
1.  **Identify the Issue**: Monitoring (Grafana) shows high 403 errors or audit logs show unexpected denials.
2.  **Revert Git Commit**:
    ```bash
    git revert HEAD
    git push origin main
    ```
    The CI/CD pipeline should automatically redeploy the previous policy bundle.
3.  **Manual OPA Rollback** (If CI/CD is slow):
    - Connect to the OPA server/cluster.
    - Push the previous `bundle.tar.gz` directly to the OPA API:
      ```bash
      curl -X PUT --data-binary @old_bundle.tar.gz http://opa-server:8181/v1/policies/disc/authz
      ```

## Prevention
- **Unit Tests**: All policies must pass `opa test` before merge.
- **Canary Deployment**: Deploy new policies to the "Canary" OPA instance first.
