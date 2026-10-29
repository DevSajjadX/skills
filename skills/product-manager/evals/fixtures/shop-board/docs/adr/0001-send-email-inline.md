# 0001 Send the Paid email inline

Status: accepted

The "Paid" email is sent inside the request that marks the order paid. There is no job queue or retry worker in v1; adding one needs a new ADR that supersedes this one.
