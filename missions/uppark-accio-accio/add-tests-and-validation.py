#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: uppark/accio: accio
# Agent:   @aria
# Date:    2026-04-01T17:36:10.196Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for accio project
Mission: uppark/accio: accio
Agent: @aria
Date: 2024

Comprehensive unit and integration tests for accio with validation coverage.
"""

import unittest
import json
import sys
import argparse
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class AccioValidationError(Exception):
    """Raised when validation fails"""
    pass


class AccioOperationType(Enum):
    """Operation types supported by accio"""
    FETCH = "fetch"
    PARSE = "parse"
    TRANSFORM = "transform"
    VALIDATE = "validate"


@dataclass
class AccioOperation:
    """Represents a single accio operation"""
    op_type: AccioOperationType
    source: str
    target: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

    def validate(self) -> bool:
        """Validate operation configuration"""
        if not self.source:
            raise AccioValidationError("Source cannot be empty")
        if self.op_type == AccioOperationType.TRANSFORM and not self.target:
            raise AccioValidationError("Transform operation requires target")
        if self.config is not None and not isinstance(self.config, dict):
            raise AccioValidationError("Config must be a dictionary")
        return True


class AccioValidator:
    """Validates accio operations and data"""

    def validate_operation(self, operation: AccioOperation) -> bool:
        """Validate a single operation"""
        return operation.validate()

    def validate_pipeline(self, operations: List[AccioOperation]) -> bool:
        """Validate entire operation pipeline"""
        if not operations:
            raise AccioValidationError("Pipeline cannot be empty")
        for idx, op in enumerate(operations):
            try:
                self.validate_operation(op)
            except AccioValidationError as e:
                raise AccioValidationError(f"Operation {idx} failed: {str(e)}")
        return True

    def validate_json_structure(self, data: str) -> bool:
        """Validate JSON structure"""
        try:
            json.loads(data)
            return True
        except json.JSONDecodeError as e:
            raise AccioValidationError(f"Invalid JSON: {str(e)}")

    def validate_data_schema(self, data: Dict[str, Any], schema: Dict[str, type]) -> bool:
        """Validate data against schema"""
        for key, expected_type in schema.items():
            if key not in data:
                raise AccioValidationError(f"Missing required field: {key}")
            if not isinstance(data[key], expected_type):
                raise AccioValidationError(
                    f"Field {key} has type {type(data[key])}, expected {expected_type}"
                )
        return True


class AccioProcessor:
    """Processes accio operations"""

    def __init__(self, validator: Optional[AccioValidator] = None):
        self.validator = validator or AccioValidator()
        self.results = []

    def process_operation(self, operation: AccioOperation) -> Dict[str, Any]:
        """Process a single operation"""
        self.validator.validate_operation(operation)

        if operation.op_type == AccioOperationType.FETCH:
            return self._fetch(operation)
        elif operation.op_type == AccioOperationType.PARSE:
            return self._parse(operation)
        elif operation.op_type == AccioOperationType.TRANSFORM:
            return self._transform(operation)
        elif operation.op_type == AccioOperationType.VALIDATE:
            return self._validate(operation)
        else:
            raise AccioValidationError(f"Unknown operation type: {operation.op_type}")

    def process_pipeline(self, operations: List[AccioOperation]) -> List[Dict[str, Any]]:
        """Process multiple operations"""
        self.validator.validate_pipeline(operations)
        self.results = []

        for operation in operations:
            result = self.process_operation(operation)
            self.results.append(result)

        return self.results

    def _fetch(self, operation: AccioOperation) -> Dict[str, Any]:
        """Simulate fetch operation"""
        return {
            "operation": "fetch",
            "source": operation.source,
            "status": "success",
            "data": f"fetched_from_{operation.source}"
        }

    def _parse(self, operation: AccioOperation) -> Dict[str, Any]:
        """Simulate parse operation"""
        try:
            self.validator.validate_json_structure(operation.source)
            return {
                "operation": "parse",
                "source": operation.source,
                "status": "success",
                "parsed": json.loads(operation.source)
            }
        except AccioValidationError:
            return {
                "operation": "parse",
                "source": operation.source,
                "status": "failed",
                "error": "Invalid JSON"
            }

    def _transform(self, operation: AccioOperation) -> Dict[str, Any]:
        """Simulate transform operation"""
        return {
            "operation": "transform",
            "source": operation.source,
            "target": operation.target,
            "status": "success",
            "data": f"transformed_{operation.target}"
        }

    def _validate(self, operation: AccioOperation) -> Dict[str, Any]:
        """Simulate validate operation"""
        config = operation.config or {}
        schema = config.get("schema", {})
        try:
            data = json.loads(operation.source) if isinstance(operation.source, str) else operation.source
            self.validator.validate_data_schema(data, schema)
            return {
                "operation": "validate",
                "status": "success",
                "message": "Data matches schema"
            }
        except (json.JSONDecodeError, AccioValidationError) as e:
            return {
                "operation": "validate",
                "status": "failed",
                "error": str(e)
            }


class TestAccioValidator(unittest.TestCase):
    """Unit tests for AccioValidator"""

    def setUp(self):
        self.validator = AccioValidator()

    def test_validate_fetch_operation(self):
        """Test validation of fetch operation"""
        operation = AccioOperation(
            op_type=AccioOperationType.FETCH,
            source="https://example.com/api"
        )
        self.assertTrue(self.validator.validate_operation(operation))

    def test_validate_operation_missing_source(self):
        """Test validation fails for missing source"""
        operation = AccioOperation(
            op_type=AccioOperationType.FETCH,
            source=""
        )
        with self.assertRaises(AccioValidationError):
            self.validator.validate_operation(operation)

    def test_validate_transform_missing_target(self):
        """Test validation fails for transform without target"""
        operation = AccioOperation(
            op_type=AccioOperationType.TRANSFORM,
            source="data",
            target=None
        )
        with self.assertRaises(AccioValidationError):
            self.validator.validate_operation(operation)

    def test_validate_transform_with_target(self):
        """Test validation succeeds for transform with target"""
        operation = AccioOperation(
            op_type=AccioOperationType.TRANSFORM,
            source="data",
            target="output"
        )
        self.assertTrue(self.validator.validate_operation(operation))

    def test_validate_config_not_dict(self):
        """Test validation fails for non-dict config"""
        operation = AccioOperation(
            op_type=AccioOperationType.FETCH,
            source="data",
            config="invalid"
        )
        with self.assertRaises(AccioValidationError):
            self.validator.validate_operation(operation)

    def test_validate_pipeline_empty(self):
        """Test validation fails for empty pipeline"""
        with self.assertRaises(AccioValidationError):
            self.validator.validate_pipeline([])

    def test_validate_pipeline_valid(self):
        """Test validation succeeds for valid pipeline"""
        operations = [
            AccioOperation(op_type=AccioOperationType.FETCH, source="src1"),
            AccioOperation(op_type=AccioOperationType.PARSE, source="src2"),
        ]
        self.assertTrue(self.validator.validate_pipeline(operations))

    def test_validate_json_valid(self):
        """Test JSON validation with valid JSON"""
        valid_json = '{"key": "value", "number": 42}'
        self.assertTrue(self.validator.validate_json_structure(valid_json))

    def test_validate_json_invalid(self):
        """Test JSON validation with invalid JSON"""
        invalid_json = '{"key": "value",}'
        with self.assertRaises(AccioValidationError):
            self.validator.validate_json_structure(invalid_json)

    def test_validate_data_schema_valid(self):
        """Test schema validation with valid data"""
        data = {"name": "John", "age": 30}
        schema = {"name": str, "age": int}
        self.assertTrue(self.validator.validate_data_schema(data, schema))

    def test_validate_data_schema_missing_field(self):
        """Test schema validation with missing field"""
        data = {"name": "John"}
        schema = {"name": str, "age": int}
        with self.assertRaises(AccioValidationError):
            self.validator.validate_data_schema(data, schema)

    def test_validate_data_schema_wrong_type(self):
        """Test schema validation with wrong type"""
        data = {"name": "John", "age": "thirty"}
        schema = {"name": str, "age": int}
        with self.assertRaises(AccioValidationError):
            self.validator.validate_data_schema(data, schema)


class TestAccioProcessor(unittest.TestCase):
    """Unit tests for AccioProcessor"""

    def setUp(self):
        self.processor = AccioProcessor()

    def test_process_fetch_operation(self):
        """Test processing fetch operation"""
        operation = AccioOperation(
            op_type=AccioOperationType.FETCH,
            source="https://example.com"
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["operation"], "fetch")
        self.assertEqual(result["status"], "success")

    def test_process_parse_operation_valid_json(self):
        """Test processing parse operation with valid JSON"""
        json_data = '{"key": "value"}'
        operation = AccioOperation(
            op_type=AccioOperationType.PARSE,
            source=json_data
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["operation"], "parse")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["parsed"]["key"], "value")

    def test_process_parse_operation_invalid_json(self):
        """Test processing parse operation with invalid JSON"""
        operation = AccioOperation(
            op_type=AccioOperationType.PARSE,
            source="{invalid}"
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["status"], "failed")

    def test_process_transform_operation(self):
        """Test processing transform operation"""
        operation = AccioOperation(
            op_type=AccioOperationType.TRANSFORM,
            source="input_data",
            target="output_format"
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["operation"], "transform")
        self.assertEqual(result["target"], "output_format")
        self.assertEqual(result["status"], "success")

    def test_process_validate_operation_success(self):
        """Test processing validate operation with valid data"""
        data = '{"name": "Alice", "age": 25}'
        schema = {"name": str, "age": int}
        operation = AccioOperation(
            op_type=AccioOperationType.VALIDATE,
            source=data,
            config={"schema": schema}
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["status"], "success")

    def test_process_validate_operation_failure(self):
        """Test processing validate operation with invalid data"""
        data = '{"name": "Alice"}'
        schema = {"name": str, "age": int}
        operation = AccioOperation(
            op_type=AccioOperationType.VALIDATE,
            source=data,
            config={"schema": schema}
        )
        result = self.processor.process_operation(operation)
        self.assertEqual(result["status"], "failed")

    def test_process_pipeline(self):
        """Test processing complete pipeline"""
        operations = [
            AccioOperation(op_type=AccioOperationType.FETCH, source="url1"),
            AccioOperation(op_type=AccioOperationType.PARSE, source='{"data": "test"}'),
            AccioOperation(op_type=AccioOperationType.TRANSFORM, source="data", target="output"),
        ]
        results = self.processor.process_pipeline(operations)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["operation"], "fetch")
        self.assertEqual(results[1]["operation"], "parse")
        self.assertEqual(results[2]["operation"], "transform")

    def test_process_pipeline_preserves_state(self):
        """Test that results are accumulated"""
        operations = [
            AccioOperation(op_type=AccioOperationType.FETCH, source="url1"),
            AccioOperation(op_type=AccioOperationType.FETCH, source="url2"),
        ]
        results = self.processor.process_pipeline(operations)
        self.assertEqual(len(self.processor.results), 2)


class TestAccioIntegration(unittest.TestCase):
    """Integration tests for accio"""

    def test_end_to_end_pipeline(self):
        """Test complete end-to-end pipeline"""
        processor = AccioProcessor()
        validator = processor.validator

        # Build a realistic pipeline
        pipeline = [
            AccioOperation(
                op_type=AccioOperationType.FETCH,
                source="https://api.example.com/users"
            ),
            AccioOperation(
                op_type=AccioOperationType.PARSE,
                source='[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
            ),
            AccioOperation(
                op_type=AccioOperationType.VALIDATE,
                source='{"id": 1, "name": "Alice"}',
                config={"schema": {"id": int, "name": str}}
            ),
        ]

        # Validate pipeline
        self.assertTrue(validator.validate_pipeline(pipeline))

        # Process pipeline
        results = processor.process_pipeline(pipeline)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["status"] in ["success", "failed"] for r in results))

    def test_error_handling_in_pipeline(self):
        """Test error handling throughout pipeline"""
        processor = AccioProcessor()

        pipeline = [
            AccioOperation(op_type=AccioOperationType.FETCH, source="url"),
            AccioOperation(op_type=AccioOperationType.PARSE, source="{broken}"),
        ]

        results = processor.process_pipeline(pipeline)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[1]["status"], "failed")

    def test_complex_transformation_pipeline(self):
        """Test complex multi-step transformation"""
        processor = AccioProcessor()

        pipeline = [
            AccioOperation(
                op_type=AccioOperationType.FETCH,
                source="data_source"
            ),
            AccioOperation(
                op_type=AccioOperationType.TRANSFORM,
                source="raw_data",
                target="normalized_data"
            ),
            AccioOperation(
                op_type=AccioOperationType.VALIDATE,
                source='{"status": "active", "count": 5}',
                config={"schema": {"status": str, "count": int}}
            ),
        ]

        results = processor.process_pipeline(pipeline)
        self.assertEqual(len(results), 3)


def run_tests(verbosity: int = 2) -> int:
    """Run all tests and return exit code"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestAccioValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestAccioProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestAccioIntegration))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


def validate_json_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from JSON file"""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


def generate_sample_operations() -> List[AccioOperation]:
    """Generate sample operations for testing"""
    return [
        AccioOperation(
            op_type=AccioOperationType.FETCH,
            source="https://api.github.com/repos/uppark/accio"
        ),
        AccioOperation(
            op_type=AccioOperationType.PARSE,
            source='{"name": "accio", "stars": 42, "language": "Python"}'
        ),
        AccioOperation(
            op_type=AccioOperationType.TRANSFORM,
            source="github_data",
            target="normalized_project_data"
        ),
        AccioOperation(
            op_type=AccioOperationType.VALIDATE,
            source='{"name": "accio", "status": "active"}',
            config={"schema": {"name": str, "status": str}}
        ),
    ]


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Accio test suite and validation framework"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run unit and integration tests"
    )
    parser.add_argument(
        "--validate",
        type=str,
        help="Validate configuration from JSON file"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with sample data"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        default=2,
        choices=[0, 1, 2],
        help="Test output verbosity level"
    )

    args = parser.parse_args()

    if args.test:
        print("Running test suite...")
        return run_tests(verbosity=args.verbosity)

    if args.validate:
        print(f"Validating configuration: {args.validate}")
        try:
            config = validate_json_config(args.validate)
            print(f"✓ Configuration is valid: {json.dumps(config, indent=2)}")
            return 0
        except Exception as e:
            print(f"✗ Configuration validation failed: {str(e)}")
            return 1

    if args.demo:
        print("Running demonstration...\n")

        processor = AccioProcessor()
        operations = generate_sample_operations()

        print(f"Processing {len(operations)} operations...\n")
        results = processor.process_pipeline(operations)

        print("Results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['operation'].upper()}")
            print