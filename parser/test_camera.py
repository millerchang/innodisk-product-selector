"""Quick test: run camera extraction on sample PDFs."""
import sys, json
sys.path.insert(0, r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\parser')
import rule_extractor

PDFS = [
    r'D:\管理\Solution Architect\Camera\1.0 Datasheet\2.0 MIPI CSI-2\EV8M-CSM1-RTCF_Datasheet_2025_Q3.pdf',
    r'D:\管理\Solution Architect\Camera\1.0 Datasheet\4.0 GMSL2\EV2F-OOM3-RHCF_Datasheet_2025_Q4.pdf',
    r'D:\管理\Solution Architect\Camera\1.0 Datasheet\5.0 Capture Card\EB120-1S4F_Datasheet_2026_May.pdf',
    r'D:\管理\Solution Architect\Camera\1.0 Datasheet\3.0 MIPI over Type-C\EV8C-OOM1-RHCF_Datasheet_2025_Q3.pdf',
]

for pdf in PDFS:
    r = rule_extractor.extract(pdf)
    pn  = r['part_no']
    cam = r.get('camera_spec', {})
    print(f"--- {pn}  (conf={r['_confidence']:.2f}, method={r['_method']}) ---")
    print(f"  iface={cam.get('interface_bus')}  res={cam.get('resolution_mp')}MP  px={cam.get('resolution_px')}  fps={cam.get('fps')}")
    print(f"  sensor_type={cam.get('sensor_type')}  size={cam.get('sensor_size')}  hdr={cam.get('hdr')}  ir={cam.get('ir_filter')}  ll={cam.get('low_light')}")
    print(f"  fov={cam.get('lens_fov_deg')}  temp={r.get('op_temp_min_c')}~{r.get('op_temp_max_c')}  certs={r.get('certifications')}")
    compat = cam.get('adapter_board_compatible', [])
    if compat:
        print(f"  compatible={compat}")
    print()
