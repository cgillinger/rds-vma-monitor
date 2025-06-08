#!/usr/bin/env python3
"""
RDS Parser - Final Clean Version
Parses JSON RDS data from redsea
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RDSParser:
    """Parse RDS JSON data from redsea output"""
    
    def __init__(self):
        self.last_valid_data = {}
        self.parse_count = 0
        self.error_count = 0
    
    def parse_line(self, line: str):
        """Parse a single line of RDS JSON data"""
        if not line or not line.strip():
            return None
            
        try:
            rds_data = json.loads(line.strip())
            self.parse_count += 1
            
            parsed = self._extract_fields(rds_data)
            parsed['timestamp'] = datetime.now().isoformat()
            
            if parsed:
                self.last_valid_data.update(parsed)
                
            return parsed
            
        except json.JSONDecodeError:
            self.error_count += 1
            logger.debug(f"JSON parse error for line: {line[:50]}...")
            return None
    
    def _extract_fields(self, rds_data: dict) -> dict:
        """Extract relevant fields from RDS data"""
        extracted = {}
        
        # Core fields for event detection
        for field in ['pi', 'ps', 'tp', 'ta', 'prog_type', 'pty', 'rt', 'ews', 'group']:
            if field in rds_data:
                if field in ['ps', 'rt']:
                    extracted[field] = rds_data[field].strip()
                else:
                    extracted[field] = rds_data[field]
        
        # Additional useful fields
        if 'di' in rds_data:
            extracted['di'] = rds_data['di']
        if 'is_music' in rds_data:
            extracted['is_music'] = rds_data['is_music']
        if 'other_network' in rds_data:
            extracted['other_network'] = rds_data['other_network']
            
        return extracted
    
    def get_stats(self) -> dict:
        """Get parser statistics"""
        return {
            'lines_parsed': self.parse_count,
            'errors': self.error_count,
            'success_rate': self.parse_count / (self.parse_count + self.error_count) if (self.parse_count + self.error_count) > 0 else 0
        }

def format_rds_summary(rds_data: dict) -> str:
    """Format RDS data for logging"""
    summary_parts = []
    
    if 'pi' in rds_data:
        summary_parts.append(f"PI:{rds_data['pi']}")
    if 'ps' in rds_data:
        summary_parts.append(f"PS:{rds_data['ps']}")
    if 'ta' in rds_data:
        summary_parts.append(f"TA:{rds_data['ta']}")
    if 'pty' in rds_data:
        summary_parts.append(f"PTY:{rds_data['pty']}")
    if 'prog_type' in rds_data:
        summary_parts.append(f"Type:{rds_data['prog_type']}")
    if 'rt' in rds_data:
        summary_parts.append(f"RT:'{rds_data['rt'][:20]}...'")
    
    return " | ".join(summary_parts)
