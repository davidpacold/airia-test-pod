#!/usr/bin/env python3
"""
Test script for Cassandra connection using credentials from aws.yaml.
This script can be used to verify the Cassandra connection independently.
"""

import os
import sys
import ssl
import time
from typing import Any, Dict

def test_cassandra_connection():
    """Test Cassandra connection with credentials from aws.yaml"""
    
    # Set environment variables based on aws.yaml
    # You can modify these based on your actual deployed pod configuration
    cassandra_config = {
        'hosts': os.getenv('CASSANDRA_HOSTS', '10.0.2.149'),
        'port': int(os.getenv('CASSANDRA_PORT', '9042')),
        'username': os.getenv('CASSANDRA_USERNAME', 'cassandra'),
        'password': os.getenv('CASSANDRA_PASSWORD', 'u1AncgPT2n'),
        'keyspace': os.getenv('CASSANDRA_KEYSPACE', 'airia'),
        'datacenter': os.getenv('CASSANDRA_DATACENTER', 'us-east-1'),
        'use_ssl': os.getenv('CASSANDRA_USE_SSL', 'false').lower() in ('true', '1', 'yes', 'on')
    }
    
    print(f"Testing Cassandra connection with configuration:")
    print(f"  Hosts: {cassandra_config['hosts']}")
    print(f"  Port: {cassandra_config['port']}")
    print(f"  Username: {cassandra_config['username']}")
    print(f"  Password: {'*' * len(cassandra_config['password'])}")
    print(f"  Keyspace: {cassandra_config['keyspace']}")
    print(f"  Datacenter: {cassandra_config['datacenter']}")
    print(f"  Use SSL: {cassandra_config['use_ssl']}")
    print()
    
    try:
        # Try to import Cassandra driver
        try:
            from cassandra.auth import PlainTextAuthProvider
            from cassandra.cluster import Cluster
            from cassandra.policies import DCAwareRoundRobinPolicy
        except ImportError as e:
            print(f"❌ Missing Cassandra driver: {e}")
            print("Install with: pip install cassandra-driver")
            return False
        
        # Build cluster configuration
        cluster_config = {
            "contact_points": [h.strip() for h in cassandra_config['hosts'].split(",")],
            "port": cassandra_config['port']
        }
        
        # Add datacenter-aware load balancing
        if cassandra_config['datacenter']:
            cluster_config["load_balancing_policy"] = DCAwareRoundRobinPolicy(
                local_dc=cassandra_config['datacenter']
            )
        
        # Add authentication
        if cassandra_config['username']:
            auth_provider = PlainTextAuthProvider(
                username=cassandra_config['username'],
                password=cassandra_config['password']
            )
            cluster_config["auth_provider"] = auth_provider
        
        # Add SSL if configured
        if cassandra_config['use_ssl']:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            cluster_config["ssl_context"] = ssl_context
        
        print("🔄 Connecting to Cassandra cluster...")
        
        # Create cluster and connect
        cluster = Cluster(**cluster_config)
        cluster.connect_timeout = 10
        
        start_time = time.time()
        session = cluster.connect(timeout=15)
        connection_time = time.time() - start_time
        
        print(f"✅ Successfully connected to Cassandra cluster (took {connection_time:.2f}s)")
        
        # Get cluster metadata
        metadata = cluster.metadata
        print(f"📊 Cluster name: {metadata.cluster_name}")
        
        # Check nodes
        nodes = []
        for host in metadata.all_hosts():
            node_info = {
                "address": host.address,
                "datacenter": host.datacenter,
                "rack": host.rack,
                "is_up": host.is_up,
                "release_version": host.release_version,
            }
            nodes.append(node_info)
        
        up_nodes = [n for n in nodes if n["is_up"]]
        print(f"📈 Nodes: {len(up_nodes)}/{len(nodes)} up")
        
        for node in nodes:
            status = "🟢 UP" if node["is_up"] else "🔴 DOWN"
            print(f"  {status} {node['address']} (DC: {node['datacenter']}, Rack: {node['rack']}, Version: {node['release_version']})")
        
        # Test basic query
        print("🔄 Testing basic query...")
        try:
            start_time = time.time()
            row = session.execute("SELECT cluster_name, release_version FROM system.local").one()
            query_time = time.time() - start_time
            print(f"✅ Query executed successfully (took {query_time:.3f}s)")
            print(f"   Cluster: {row.cluster_name}, Version: {row.release_version}")
        except Exception as e:
            print(f"⚠️  Query failed: {e}")
        
        # List keyspaces
        print("🔄 Listing keyspaces...")
        try:
            rows = session.execute("SELECT keyspace_name FROM system_schema.keyspaces")
            system_keyspaces = {'system', 'system_schema', 'system_auth', 'system_distributed', 'system_traces'}
            keyspaces = [row.keyspace_name for row in rows if row.keyspace_name not in system_keyspaces]
            print(f"📋 Found {len(keyspaces)} user keyspaces: {', '.join(keyspaces) if keyspaces else 'none'}")
            
            # Check if configured keyspace exists
            if cassandra_config['keyspace']:
                if cassandra_config['keyspace'] in keyspaces:
                    print(f"✅ Configured keyspace '{cassandra_config['keyspace']}' found")
                else:
                    print(f"⚠️  Configured keyspace '{cassandra_config['keyspace']}' not found")
                    
        except Exception as e:
            print(f"⚠️  Failed to list keyspaces: {e}")
        
        # Clean up
        session.shutdown()
        cluster.shutdown()
        
        print("🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"💡 Troubleshooting tips:")
        
        error_msg = str(e).lower()
        if "authentication" in error_msg or "credentials" in error_msg:
            print("   - Verify username and password are correct")
            print("   - Check if authentication is enabled on the cluster")
        elif "connection refused" in error_msg or "cannot connect" in error_msg:
            print("   - Check if Cassandra hosts are reachable")
            print("   - Verify port is correct (usually 9042)")
            print("   - Check firewall rules")
        elif "timeout" in error_msg:
            print("   - Check network connectivity")
            print("   - Verify Cassandra service is running")
            print("   - Consider increasing timeout")
        elif "no hosts available" in error_msg:
            print("   - Verify host addresses are correct and accessible")
            print("   - Check if DNS resolution is working")
        elif "datacenter" in error_msg:
            print("   - Check datacenter name matches your cluster configuration")
        
        return False

if __name__ == "__main__":
    # You can override these with environment variables
    print("🧪 Cassandra Connection Test")
    print("=" * 50)
    
    success = test_cassandra_connection()
    sys.exit(0 if success else 1)