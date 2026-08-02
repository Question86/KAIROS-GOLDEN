# KAIROS Golden Starter

This private template contains the verified KAIROS harness and a sanitized source-only
starter workspace. It contains only generic bootstrap history, one mandatory Loop 1
archive, and a cryptographic golden seal. It contains no developer project-task history.

The first project command is project-kickoff. Run it from kairos_harness with an inline
kairos-project-kickoff/v1 JSON contract. KAIROS reconstructs the derived metadata,
verifies the sealed Loop 1 archive, creates a fresh verified backup, stages the new goal
and first task, and atomically opens Loop 2.

The golden seal is immutable. Ongoing project work belongs in repositories created from
this template, never in the template repository itself.
