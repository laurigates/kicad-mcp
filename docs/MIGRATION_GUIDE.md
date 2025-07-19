# S-expression Implementation Migration Guide

This guide provides step-by-step instructions for migrating from the original `SExpressionGenerator` to the new `SExpressionHandler` implementation.

## Overview

The KiCad MCP project has transitioned from a string-based S-expression generator to a new `sexpdata`-based handler for improved KiCad format compatibility and maintainability. This migration includes:

- **New Implementation**: `SExpressionHandler` using the `sexpdata` library
- **Feature Flag System**: Gradual rollout with fallback mechanisms
- **Migration Tools**: Automated validation and planning utilities
- **Zero-Downtime Migration**: Seamless transition without service interruption

## Prerequisites

Before starting the migration, ensure you have:

1. **Python Environment**: Python 3.8+ with required dependencies
2. **Testing Environment**: Access to test KiCad projects and files
3. **Monitoring Tools**: Ability to monitor error rates and performance
4. **Rollback Plan**: Understanding of how to quickly revert changes

## Migration Phases

### Phase 1: Preparation and Validation (Days 1-3)

#### 1.1 Environment Setup

Set the required environment variables:

```bash
export KICAD_MCP_ENABLE_SEXPR_HANDLER=true
export KICAD_MCP_ENABLE_SEXPR_FALLBACK=true
export KICAD_MCP_VALIDATE_SEXPR_OUTPUT=true
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=0
```

#### 1.2 Run Migration Validation

Execute the migration validation tool:

```bash
python -m kicad_mcp.utils.migration_utils
```

Expected output for a ready system:
```
=== MIGRATION VALIDATION RESULTS ===
Timestamp: 2024-07-18T10:30:00
Ready for migration: ✅ YES

CHECK RESULTS:
  ✅ environment: Environment configuration is correct
  ✅ feature_flags: Feature flags are properly configured
  ✅ compatibility: Implementation compatibility excellent: 95.0%
  ✅ test_coverage: Test coverage is adequate

RECOMMENDATIONS:
  1. System is ready for migration

🎉 System is ready for migration!
```

#### 1.3 Set Up Monitoring

Configure monitoring for:
- Error rates
- Performance metrics
- S-expression validation failures
- Fallback occurrences

#### 1.4 Test Rollback Procedures

Verify you can quickly revert to the original implementation:

```bash
export KICAD_MCP_SEXPR_IMPLEMENTATION=generator
export KICAD_MCP_ENABLE_SEXPR_HANDLER=false
```

### Phase 2: Canary Deployment (Days 4-7)

#### 2.1 Enable Canary Rollout

```bash
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=5
export KICAD_MCP_ENABLE_SEXPR_COMPARISON=true
export KICAD_MCP_ENABLE_PERFORMANCE_LOGGING=true
```

#### 2.2 Monitor Key Metrics

- **Error Rate**: Should remain < 0.1%
- **Performance**: Should be within 20% of baseline
- **Compatibility**: Should maintain > 95% compatibility rate

#### 2.3 Review A/B Comparison Results

Check logs for comparison results:
```bash
grep "Implementation outputs" /var/log/kicad-mcp.log
```

#### 2.4 Success Criteria

- No increase in error rates
- Performance acceptable
- User feedback positive
- Compatibility metrics good

### Phase 3: Gradual Rollout (Days 8-14)

Gradually increase rollout percentage:

#### 3.1 10% Rollout
```bash
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=10
```

#### 3.2 25% Rollout
```bash
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=25
```

#### 3.3 50% Rollout
```bash
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=50
```

#### 3.4 75% Rollout
```bash
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=75
```

**Monitor at each step**: Allow 1-2 days between increases to observe system behavior.

### Phase 4: Full Deployment (Days 15-16)

#### 4.1 Complete Migration
```bash
export KICAD_MCP_SEXPR_IMPLEMENTATION=handler
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=100
export KICAD_MCP_ENABLE_SEXPR_COMPARISON=false
```

#### 4.2 Final Validation

Run a final validation to confirm successful migration:

```bash
python -c "
from kicad_mcp.utils.sexpr_service import get_sexpr_service
service = get_sexpr_service()
print('Current implementation:', service.get_config_info()['primary_implementation'])
print('Handler enabled:', service.get_config_info()['handler_enabled'])
"
```

### Phase 5: Cleanup and Documentation (Days 17-18)

#### 5.1 Update Documentation

- Update API documentation
- Update deployment guides
- Create performance baselines

#### 5.2 Plan Deprecation

Create a plan for eventually removing the old implementation:
- Set deprecation timeline (6+ months)
- Communicate to stakeholders
- Update migration documentation

## Environment Variable Reference

| Variable | Purpose | Values | Default |
|----------|---------|--------|---------|
| `KICAD_MCP_SEXPR_IMPLEMENTATION` | Primary implementation | `generator`, `handler`, `auto` | `generator` |
| `KICAD_MCP_ENABLE_SEXPR_HANDLER` | Enable new handler | `true`, `false` | `false` |
| `KICAD_MCP_ENABLE_SEXPR_FALLBACK` | Enable fallback on errors | `true`, `false` | `true` |
| `KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE` | Rollout percentage | `0-100` | `0` |
| `KICAD_MCP_ENABLE_SEXPR_COMPARISON` | Enable A/B testing | `true`, `false` | `false` |
| `KICAD_MCP_VALIDATE_SEXPR_OUTPUT` | Validate generated output | `true`, `false` | `false` |
| `KICAD_MCP_STRICT_SEXPR_VALIDATION` | Strict validation mode | `true`, `false` | `false` |
| `KICAD_MCP_ENABLE_PERFORMANCE_LOGGING` | Log performance metrics | `true`, `false` | `false` |

## Monitoring and Troubleshooting

### Key Metrics to Monitor

1. **Error Rates**
   - S-expression generation failures
   - Validation failures
   - Fallback occurrences

2. **Performance Metrics**
   - Generation time comparison
   - Memory usage
   - CPU utilization

3. **Compatibility Metrics**
   - Structural equality percentage
   - KiCad file validation success rate

### Common Issues and Solutions

#### High Error Rates

**Symptoms**: Increased error rates in logs
**Solution**:
1. Check environment variable configuration
2. Verify handler dependencies are installed
3. Consider reducing rollout percentage
4. Review error logs for specific issues

#### Performance Degradation

**Symptoms**: Slower S-expression generation
**Solution**:
1. Review performance logs
2. Check system resources
3. Consider optimizing handler implementation
4. Temporarily reduce rollout percentage

#### Compatibility Issues

**Symptoms**: A/B comparison failures
**Solution**:
1. Review specific failing test cases
2. Check for recent changes in components or connections
3. Update handler logic if needed
4. Consult development team

### Emergency Rollback

If critical issues arise, immediately rollback:

```bash
# Emergency rollback - revert to original implementation
export KICAD_MCP_SEXPR_IMPLEMENTATION=generator
export KICAD_MCP_ENABLE_SEXPR_HANDLER=false
export KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE=0

# Restart services if needed
systemctl restart kicad-mcp  # or equivalent
```

## Testing Checklist

Before each phase, verify:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Migration validation passes
- [ ] Monitoring systems operational
- [ ] Rollback procedures tested
- [ ] Stakeholders notified

During each phase, monitor:

- [ ] Error rates remain stable
- [ ] Performance within acceptable bounds
- [ ] No user complaints
- [ ] Compatibility metrics good
- [ ] Logs show expected behavior

## Success Criteria

The migration is considered successful when:

1. **100% rollout** achieved without issues
2. **Error rates** remain at or below baseline
3. **Performance** meets or exceeds original implementation
4. **User feedback** is positive
5. **All tests** continue to pass
6. **Documentation** is updated and complete

## Support and Contacts

For migration support:

- **Technical Issues**: Check project GitHub issues
- **Performance Concerns**: Review monitoring dashboards
- **Emergency Rollback**: Follow emergency procedures above

## Migration Timeline

| Phase | Duration | Rollout % | Key Activities |
|-------|----------|-----------|----------------|
| 1 | 3 days | 0% | Preparation and validation |
| 2 | 4 days | 5% | Canary deployment |
| 3a | 1-2 days | 10% | Initial gradual rollout |
| 3b | 1-2 days | 25% | Continue rollout |
| 3c | 1-2 days | 50% | Majority rollout |
| 3d | 1-2 days | 75% | Near-complete rollout |
| 4 | 2 days | 100% | Full deployment |
| 5 | 2 days | 100% | Cleanup and documentation |

**Total Estimated Duration**: 2-4 weeks

This conservative timeline allows for careful monitoring and adjustment at each step to ensure a successful, zero-downtime migration.
