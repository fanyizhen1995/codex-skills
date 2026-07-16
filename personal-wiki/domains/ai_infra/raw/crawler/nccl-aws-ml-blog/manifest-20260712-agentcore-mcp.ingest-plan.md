# Ingest Plan

Source path: `raw/crawler/nccl-aws-ml-blog/manifest-20260712-agentcore-mcp.json`

## Durable Claims

- The July 12 local AWS ML Blog capture is a new local URL identity for an Amazon Bedrock AgentCore ecommerce MCP server walkthrough with Mistral AI Studio. It is not a duplicate of the Hitchhiker paper's conceptual MCP/A2A reference, and parent-26 explicitly did not ingest the adjacent AgentCore MCP capture.
- AgentCore Runtime is source-described as fully managed serverless hosting for agent and MCP workloads with session isolation, long-running request support, built-in JWT validation, observability, and managed container/load-balancer/auth-middleware responsibilities.
- The MCP server is Python plus FastMCP, exposes six tools through `/mcp`, exposes `/health`, uses `stateless_http=True` for AgentCore load balancing, and relies on function parameters, type hints, and docstrings as tool schemas.
- Authentication is split into infrastructure JWT validation by AgentCore Runtime and application-level Cognito identity resolution. The source covers OAuth 2.1 login, Cognito JWT issuance, `customJWTAuthorizer`, allowed client IDs, Authorization header forwarding, `custom:customer_id` lookup, tool-level authentication checks, and customer-scoped data ownership checks.
- The DynamoDB data boundary is five tables: Products, Customers, Orders, Reviews, and Returns, with on-demand capacity and Global Secondary Indexes. This is promoted only as an MCP tool data-boundary example, not as generic ecommerce guidance.
- Deployment surfaces include AWS CDK stacks, IAM role creation, ECR repository provisioning, SSM Parameter Store values, AgentCore CLI configuration, CodeBuild cloud image build, S3 source upload, ECR image push, and Bedrock AgentCore API runtime creation. Docker is not required locally in the walkthrough because AgentCore Runtime builds container images in the cloud using AWS CodeBuild.
- Security and connector controls include least privilege IAM for `GetItem`, `PutItem`, and `Query` on named DynamoDB table ARNs, AgentCore Policy for tool-call boundaries, AgentCore Gateway for API management, token descoping before tool forwarding, trusted MCP connector guidance for Mistral Vibe, OAuth or expiring-token authentication, secure connections, and session handling.
- Operational hooks are limited to source-mentioned CloudWatch permissions/dashboards, AWS WAF request filtering, and Amazon EventBridge notifications. They are not production SLOs, validated alert thresholds, incident evidence, or dashboard screenshots.
- Cold-start/session behavior is source-stated only: first invocation has a 10 to 20 second cold start while the container initializes, and subsequent requests within the session respond in milliseconds.

## Target Pages

- Update `wiki/references/inference-runtime-infrastructure.md` with a bounded AgentCore MCP Runtime section covering Runtime hosting, FastMCP/stateless HTTP, deployment build surfaces, and cold-start/session behavior.
- Update `wiki/references/security-governance-cost-infrastructure.md` with JWT/OAuth/Cognito, least privilege IAM, AgentCore Policy/Gateway, token descoping, and trusted connector boundaries.
- Update `wiki/references/data-rag-pipeline-infrastructure.md` with the DynamoDB customer-scoped tool data boundary, explicitly not a RAG propagation or generic ecommerce page.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so semantic parent-27 is discoverable.

## Non-Goals

- Do not fetch AWS docs, GitHub repositories, Mistral docs, or external pages.
- Do not ingest adjacent AWS Nemotron, NVIDIA GQE/Presto, NCCL GitHub issues/releases, vLLM refreshes, or other July 12 captures.
- Do not treat this walkthrough as proof of production deployment, independent security audit, legal compliance, production incident/postmortem, service SLO, local benchmark, or full RAG propagation run.
- Do not promote generic ecommerce application behavior, model-quality claims, Mistral product positioning, or user-experience guidance unless it defines MCP/agent infrastructure boundaries.
- Do not create accelerator catalog rows, structured hardware data, training benchmark rows, storage/fabric benchmark rows, SGLang closure evidence, or NCCL release evidence.
- Do not modify crawler backend/frontend, Loop Dashboard, harness code, dependencies, generated files, runtime logs, secrets, or unrelated dirty paths.

## Compact Decision

The raw AWS ML Blog capture is readable and small enough to inspect directly. Keep it as Markdown under `raw/crawler/nccl-aws-ml-blog/`; no gzip compaction is needed.
