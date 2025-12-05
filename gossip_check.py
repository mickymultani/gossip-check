import requests
import random
import csv
import json
import os
from datetime import datetime
from collections import Counter

# --- Configuration ---
# Public Solana RPC endpoint (Mainnet Beta)
RPC_URL = "https://api.mainnet-beta.solana.com"
# Free IP Geolocation API (ip-api.com allows 45 requests/min, or batch requests)
GEO_API_BATCH_URL = "http://ip-api.com/batch"
# Target sample size
SAMPLE_SIZE = 150

# OFAC Sanctioned Countries (ISO 3166-1 alpha-2 codes)
# Includes: Iran (IR), North Korea (KP), Cuba (CU), Syria (SY), 
# Russia (RU), Belarus (BY), Venezuela (VE), Myanmar (MM)
OFAC_COUNTRIES = {'IR', 'KP', 'CU', 'SY', 'RU', 'BY', 'VE', 'MM'}

def get_gossip_nodes():
    """Queries the Solana RPC for the current cluster nodes (gossip view)."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getClusterNodes"
    }
    try:
        response = requests.post(RPC_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if 'result' in data:
            return data['result']
    except Exception as e:
        print(f"Error fetching cluster nodes: {e}")
        return []
    return []

def get_ip_country_batch(ips):
    """
    Geolocates a list of IPs using ip-api.com batch endpoint.
    Returns a dictionary: {ip: country_code}
    """
    results = {}
    # ip-api batch limit is 100 per request, so we chunk it
    chunk_size = 100
    for i in range(0, len(ips), chunk_size):
        chunk = ips[i:i + chunk_size]
        try:
            # We request only the query (IP) and countryCode fields to save bandwidth
            payload = [{"query": ip, "fields": "query,country,countryCode"} for ip in chunk]
            response = requests.post(GEO_API_BATCH_URL, json=payload, timeout=20)
            data = response.json()
            
            for item in data:
                # Store country code (e.g., 'US', 'RU')
                results[item['query']] = {
                    'code': item.get('countryCode', 'Unknown'),
                    'name': item.get('country', 'Unknown')
                }
        except Exception as e:
            print(f"Error geolocating chunk {i}: {e}")
    return results

def main():
    print("Fetching nodes from Solana Gossip Network...")
    nodes = get_gossip_nodes()
    
    # Filter nodes that have a valid gossip IP (sometimes they are null or private)
    valid_nodes = [n for n in nodes if n.get('gossip')]
    print(f"Total active nodes found: {len(valid_nodes)}")

    # Random Sampling
    if len(valid_nodes) > SAMPLE_SIZE:
        sampled_nodes = random.sample(valid_nodes, SAMPLE_SIZE)
    else:
        sampled_nodes = valid_nodes
    
    print(f"Sampling {len(sampled_nodes)} nodes...")

    # Extract IPs (stripping port numbers if present)
    # Gossip format is usually "IP:PORT"
    ip_list = []
    node_map = {} # Map IP back to node info for CSV
    
    for node in sampled_nodes:
        gossip_addr = node.get('gossip')
        if gossip_addr:
            ip = gossip_addr.split(':')[0]
            ip_list.append(ip)
            node_map[ip] = node

    # Geolocate
    geo_data = get_ip_country_batch(ip_list)

    # Process Data
    processed_data = []
    country_counter = Counter()
    sanctioned_count = 0
    
    for ip, node in node_map.items():
        location = geo_data.get(ip, {'code': 'XX', 'name': 'Unknown'})
        country_code = location['code']
        country_name = location['name']
        
        is_sanctioned = country_code in OFAC_COUNTRIES
        if is_sanctioned:
            sanctioned_count += 1
            
        country_counter[country_code] += 1
        
        processed_data.append({
            "timestamp": datetime.now().isoformat(),
            "pubkey": node.get('pubkey'),
            "gossip_ip": ip,
            "version": node.get('version'),
            "country_code": country_code,
            "country_name": country_name,
            "is_ofac_sanctioned": is_sanctioned
        })

    # --- Generate Outputs ---

    # 1. Write CSV
    csv_filename = "daily_node_scan.csv"
    # Check if file exists to decide whether to write headers (append mode)
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, 'a', newline='') as f:
        fieldnames = ["timestamp", "pubkey", "gossip_ip", "version", "country_code", "country_name", "is_ofac_sanctioned"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(processed_data)
    
    print(f"Results appended to {csv_filename}")

    # 2. Write Summary Text File
    total_fetched = len(processed_data)
    non_compliance_pct = (sanctioned_count / total_fetched * 100) if total_fetched > 0 else 0
    
    summary_lines = [
        f"--- Solana Gossip Node Scan Summary ---",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Nodes Sampled: {total_fetched}",
        f"---------------------------------------",
        f"Sanctioned Nodes (OFAC): {sanctioned_count}",
        f"Non-Compliance Percentage: {non_compliance_pct:.2f}%",
        f"---------------------------------------",
        f"Top Countries:",
        f"  🇺🇸 US (USA): {country_counter.get('US', 0)}",
        f"  🇩🇪 DE (Germany): {country_counter.get('DE', 0)}",
        f"  🇷🇺 RU (Russia): {country_counter.get('RU', 0)}",
        f"  🇮🇷 IR (Iran): {country_counter.get('IR', 0)}",
        f"  🇰🇵 KP (North Korea): {country_counter.get('KP', 0)}",
        f"  Other: {total_fetched - sum(country_counter.values())}", # Just for logic check
        f"---------------------------------------",
        f"Full Country Breakdown:",
    ]
    
    for code, count in country_counter.most_common():
        summary_lines.append(f"  {code}: {count}")

    with open("daily_summary.txt", "w") as f:
        f.write("\n".join(summary_lines))

    print("Summary generated in daily_summary.txt")

if __name__ == "__main__":
    main()
