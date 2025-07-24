//Maya ASCII 2022 scene
//Name: tpl_biped.ma
//Last modified: Thu, Jun 26, 2025 12:50:55 PM
//Codeset: 1252
requires maya "2022";
requires "stereoCamera" "10.0";
currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2022";
fileInfo "version" "2022";
fileInfo "cutIdentifier" "202110272215-ad32f8f1e6";
fileInfo "osv" "Windows 10 Pro for Workstations v2009 (Build: 19045)";
fileInfo "UUID" "7DF4F2B7-4732-6DA7-0794-758CD1CDCD66";
createNode transform -n "asset";
	rename -uid "A31BD992-4137-B1E3-02FC-ED915A46E9B8";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_index" -ln "gem_index" -at "long";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_group" -ln "gem_group" -dt "string";
	addAttr -r false -ci true -m -im false -sn "gem_dag_children" -ln "gem_dag_children" 
		-dt "string";
	addAttr -ci true -sn "gem_version" -ln "gem_version" -dt "string";
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 1 0.73000002 0.33000001 ;
	setAttr -l on ".gem_type" -type "string" "asset";
	setAttr ".gem_id" -type "string" "gemini";
	setAttr ".gem_group" -type "string" "all";
	setAttr -s 4 ".gem_dag_children";
	setAttr ".gem_dag_children[0]" -type "string" "spine::skin.pelvis";
	setAttr ".gem_dag_children[1]" -type "string" "spine::skin.pelvis";
	setAttr ".gem_dag_children[2]" -type "string" "spine::skin.pelvis";
	setAttr ".gem_dag_children[3]" -type "string" "spine::skin.pelvis";
	setAttr ".gem_version" -type "string" "0.1.0 (dev)";
createNode transform -n "template" -p "asset";
	rename -uid "B338630C-457B-4495-8F1C-6FB6A107BFB1";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	setAttr ".gem_id" -type "string" "::template";
createNode joint -n "tpl_world" -p "template";
	rename -uid "20A3B924-4338-4520-46B2-F4BFA734AC9C";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	setAttr ".ds" 2;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "world";
	setAttr ".gem_module" -type "string" "world.character";
	setAttr ".gem_template" -type "string" "[template]\ndesc: default world for character. add a fly and squash controllers\n\nstructure:\n  world: .\n  root: /1\n\nnames:\n  world: WORLD\n  move: MOVE\n  fly: fly\n  scale: scale";
	setAttr ".gem_hook" -type "string" "world::hooks.world";
	setAttr ".gem_dag_ctrls" -type "string" "world::ctrls.move";
createNode joint -n "tpl_world_root" -p "tpl_world";
	rename -uid "AF4A8EBE-462B-9319-1009-D480794D5171";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	setAttr ".t" -type "double3" 0 12.487684139478215 0.20572209212730633 ;
	setAttr ".gem_hook" -type "string" "world::hooks.root";
	setAttr ".gem_dag_ctrls" -type "string" "world::ctrls.scale";
createNode joint -n "tpl_spine" -p "tpl_world_root";
	rename -uid "0CB6E4C6-4BDF-756B-4829-FB8DF78AA864";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "gem_enable_modes" -ln "gem_enable_modes" -dt "string";
	addAttr -ci true -k true -sn "gem_opt_pivots" -ln "gem_opt_pivots" -min 0 -max 2 
		-en "legacy:spine1:centered" -at "enum";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 -1.3238103429824477 -0.06356122944305645 ;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "spine";
	setAttr ".gem_module" -type "string" "spine.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy spine from ttRig3\n\nstructure:\n  root: .\n  chain: /*\n  hips:\n  spine1: /1\n  spine2: /2\n  tip: /-1\n  mid: spine1+spine2\n\nnames:\n  spine: spine\n  cog: cog\n  pelvis: pelvis\n  hip: hip\n  shoulder: shoulder\n\nopts:\n  group:\n    value: body\n  merge:\n    value: 1\n  flip:\n    value: x\n\n  bones:\n    value: 6\n  bones_length:\n    value: 0\n    enum:\n     0: equal\n     1: parametric\n\n  orient_spine:\n    value: off\n  orient_pelvis:\n    value: off\n  orient_shoulders:\n    value: off\n  pivots:\n    value: 0\n    enum:\n     0: legacy\n     1: centered IK\n\n  default_stretch:\n    value: on";
	setAttr ".gem_enable_modes" -type "string" "~release-layout";
	setAttr -k on ".gem_opt_pivots" 2;
	setAttr ".gem_hook" -type "string" "spine::hooks.spine.0";
	setAttr ".gem_dag_ctrls" -type "string" "spine::ctrls.spine1";
	setAttr ".gem_dag_skin" -type "string" "spine::skin.0";
createNode joint -n "tpl_spine_chain1" -p "tpl_spine";
	rename -uid "A17E9122-4939-0E1B-CBCA-BDBAD1000231";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.79335327721757842 0.12540181317023269 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_hook" -type "string" "spine::hooks.spine.1";
	setAttr ".gem_dag_skin" -type "string" "spine::skin.2";
createNode joint -n "tpl_spine_chain2" -p "tpl_spine_chain1";
	rename -uid "E04325E9-404A-0C17-C4F5-F28CB7F497E6";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.92946025614471139 0.025733646998586379 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_hook" -type "string" "spine::hooks.spine.2";
	setAttr ".gem_dag_ctrls" -type "string" "spine::ctrls.spine2";
	setAttr ".gem_dag_skin" -type "string" "spine::skin.4";
createNode joint -n "tpl_spine_tip" -p "tpl_spine_chain2";
	rename -uid "9C979204-446C-41D5-8E7F-16A536FBD7D5";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 1.0189512412694404 -0.16966736383089925 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_hook" -type "string" "spine::hooks.shoulders";
	setAttr ".gem_dag_ctrls" -type "string" "spine::ctrls.spineIK";
	setAttr ".gem_dag_skin" -type "string" "spine::skin.6";
createNode joint -n "tpl_arm" -p "tpl_spine_tip";
	rename -uid "B55EF9B7-40C0-71B9-BD7E-0DAC92F11FBF";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "nts" -ln "notes" -dt "string";
	addAttr -ci true -sn "gem_opt_forks" -ln "gem_opt_forks" -dt "string";
	addAttr -ci true -sn "gem_var_auto_translate" -ln "gem_var_auto_translate" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_base_0" -ln "gem_var_shear_up_base_0" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_base_1" -ln "gem_var_shear_up_base_1" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_tip_2" -ln "gem_var_shear_up_tip_2" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_tip_3" -ln "gem_var_shear_up_tip_3" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_base_0" -ln "gem_var_shear_dn_base_0" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_base_1" -ln "gem_var_shear_dn_base_1" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_tip_2" -ln "gem_var_shear_dn_tip_2" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_tip_3" -ln "gem_var_shear_dn_tip_3" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_0" -ln "gem_var_tw_dn_0" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_1" -ln "gem_var_tw_dn_1" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_2" -ln "gem_var_tw_dn_2" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_3" -ln "gem_var_tw_dn_3" -at "double";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 1.2550352811813354 0.50884449924603814 -0.18531318750203191 ;
	setAttr ".r" -type "double3" -3.2631081685818493 0 -47.343533690055466 ;
	setAttr ".jo" -type "double3" 0 0 -89.999999999999986 ;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "arm";
	setAttr ".gem_module" -type "string" "arm.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy arm from ttRig3\n\nstructure:\n  clavicle:\n  limb1: .\n  limb2: /1\n  limb3: /2\n  digits: /3\n  tip: /4\n  heel:\n\nnames:\n  limb: arm\n  clavicle: clav\n  limb1: shoulder\n  limb2: elbow\n  limb3: wrist\n  digits: fingers\n  effector: hand\n  heel: paw\n\nopts:\n  forks:\n    value: \"['L', 'R']\"\n    literal: on\n  merge:\n    value: 1\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: -z\n  up_axis2:\n    value: -x\n\n  reverse_lock:\n    value: off\n  clavicle:\n    value: on\n  pv_space:\n    value: ''\n\n  default_stretch:\n    value: on\n  soft_distance:\n    value: 0.05\n    min: 0\n    max: 1\n\n  blend_joints:\n    value: on\n\n  twist_joints_up:\n    value: 3\n    min: 2\n  twist_joints_dn:\n    value: 3\n    min: 2\n  deform_chains:\n    value: 1\n    min: 1\n    max: 5";
	setAttr ".nts" -type "string" "[mod]\n# -- arm settings\n\nplug:\n node: arm.L::weights.0\n\n twist_dn_0: $tw_dn_0\n twist_dn_1: $tw_dn_1\n twist_dn_2: $tw_dn_2\n twist_dn_3: $tw_dn_3\n\n shear_up_base_0: $shear_up_base_0\n shear_up_base_1: $shear_up_base_1\n shear_up_tip_2:  $shear_up_tip_2\n shear_up_tip_3:  $shear_up_tip_3\n shear_dn_base_0: $shear_dn_base_0\n shear_dn_base_1: $shear_dn_base_1\n shear_dn_tip_2:  $shear_dn_tip_2\n shear_dn_tip_3:  $shear_dn_tip_3\n\nplug:\n  node: arm.L::ctrls.clavicle\n  auto_translate:\n    set: $auto_translate\n";
	setAttr ".gem_opt_forks" -type "string" "[L, R]";
	setAttr -k on ".gem_var_auto_translate";
	setAttr -k on ".gem_var_shear_up_base_0" 0.8;
	setAttr -k on ".gem_var_shear_up_base_1";
	setAttr -k on ".gem_var_shear_up_tip_2";
	setAttr -k on ".gem_var_shear_up_tip_3" 0.75;
	setAttr -k on ".gem_var_shear_dn_base_0" 0.75;
	setAttr -k on ".gem_var_shear_dn_base_1";
	setAttr -k on ".gem_var_shear_dn_tip_2";
	setAttr -k on ".gem_var_shear_dn_tip_3" 0.5;
	setAttr -k on ".gem_var_tw_dn_0" 0.15;
	setAttr -k on ".gem_var_tw_dn_1" 0.2;
	setAttr -k on ".gem_var_tw_dn_2" 0.4;
	setAttr -k on ".gem_var_tw_dn_3" 0.85;
	setAttr ".gem_hook" -type "string" "arm.L::hooks.limb1";
	setAttr ".gem_dag_ctrls" -type "string" "arm.L::ctrls.limb1";
	setAttr ".gem_dag_skin" -type "string" "arm.L::skin.up.0";
createNode joint -n "tpl_arm_limb2" -p "tpl_arm";
	rename -uid "B22F608F-4DAA-7FFF-DEC3-E39CB82CB781";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.03980734006191252 2.7094530334836948 -0.040785519372157859 ;
	setAttr ".r" -type "double3" 6.5098320481494474 0 0 ;
	setAttr ".gem_hook" -type "string" "arm.L::hooks.limb2";
	setAttr ".gem_dag_ctrls" -type "string" "arm.L::ctrls.limb2";
	setAttr ".gem_dag_skin" -type "string" "arm.L::skin.dn.0";
createNode joint -n "tpl_arm_limb3" -p "tpl_arm_limb2";
	rename -uid "071F0C64-4557-67DE-7ED8-67B3BD53C276";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.018843310031670502 2.6711222700605881 0.045328318066271488 ;
	setAttr ".r" -type "double3" -6.7772342820626221 0 -5.2123313750370848 ;
	setAttr ".jo" -type "double3" 0 -89.999999999999986 0 ;
	setAttr ".radi" 2;
	setAttr ".gem_hook" -type "string" "arm.L::hooks.effector";
	setAttr ".gem_dag_ctrls" -type "string" "arm.L::ctrls.limb3";
	setAttr ".gem_dag_skin" -type "string" "arm.L::hooks.effector";
createNode joint -n "tpl_arm_digits" -p "tpl_arm_limb3";
	rename -uid "CC7F37B0-4FC0-F2A5-BDC8-26A607F4FE22";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -1.0830163263593484e-17 0.71030587822426761 0.029528390163688467 ;
	setAttr ".gem_hook" -type "string" "arm.L::hooks.digits";
	setAttr ".gem_dag_skin" -type "string" "arm.L::hooks.digits";
createNode joint -n "tpl_arm_tip" -p "tpl_arm_digits";
	rename -uid "F286C306-4B46-5F9F-9979-BD99423B5CDC";
	setAttr ".t" -type "double3" 0 0.94901812150038745 -0.062529074683296076 ;
createNode transform -n "_shape_arm_digits_L" -p "tpl_arm_digits";
	rename -uid "B4122AB0-43FC-D931-CC06-4596F469332B";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.digits";
createNode transform -n "shp_arm_digits_L" -p "_shape_arm_digits_L";
	rename -uid "518BDFC8-44F6-F9FF-1CBB-0580CA1E223A";
	setAttr ".t" -type "double3" -1.1102230246251565e-16 1.7763568394002505e-15 3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" 0 180 0 ;
	setAttr ".s" -type "double3" 1.2887182654656475 1.2887182654656502 0.7240398443267404 ;
createNode nurbsCurve -n "circleShape" -p "shp_arm_digits_L";
	rename -uid "CB361A85-4E7E-E0E4-5251-82925A422F55";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99609375 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35355343722788868 2.1648905778322359e-17 -0.35355343722788973
		-1.1797478942098477e-16 3.0616175867864385e-17 -0.50000010466894873
		-0.35355343722788879 2.1648905778322359e-17 -0.35355343722788973
		-0.50000010466894784 8.8718018035724711e-33 -1.1197796093639674e-15
		-0.35355343722788879 -2.1648905778322359e-17 0.35355343722788773
		-2.1159053728755823e-16 -3.0616175867864385e-17 0.50000010466894673
		0.35355343722788868 -2.1648905778322359e-17 0.35355343722788773
		0.50000010466894762 -1.6444006791919543e-32 -7.0634106565081731e-16
		0.35355343722788868 2.1648905778322359e-17 -0.35355343722788973
		-1.1797478942098477e-16 3.0616175867864385e-17 -0.50000010466894873
		-0.35355343722788879 2.1648905778322359e-17 -0.35355343722788973
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_arm_digits_L_pointConstraint1" -p "_shape_arm_digits_L";
	rename -uid "4764130E-4A26-CD5E-01E2-E78A7D006C65";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_digitsW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" -1.1102230246251565e-16 1.7763568394002505e-15 -1.7763568394002505e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_digits_L_aimConstraint1" -p "_shape_arm_digits_L";
	rename -uid "B082AB06-42C4-6BFA-0D22-A191DCF5CF38";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_tipW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -3.7696657830205904 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_ik_L" -p "tpl_arm_digits";
	rename -uid "11D5910F-4994-9704-FB03-40847F0B8CE2";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.ik";
createNode transform -n "shp_arm_ik_L" -p "_shape_arm_ik_L";
	rename -uid "AD60CC05-4731-4A2D-8E71-D3918F07D0C0";
	setAttr ".t" -type "double3" 4.4408920985006262e-16 1.2434497875801753e-14 -0.041086975912287826 ;
	setAttr ".s" -type "double3" 1.1505569962149165 1.1505569962149214 1.1505569962149214 ;
createNode nurbsCurve -n "rhombusShape" -p "shp_arm_ik_L";
	rename -uid "D2099680-47B3-39FC-A77C-168507AC49C2";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99609375 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 4 0 no 3
		5 0 1 2 3 4
		5
		1 0 0
		0 0 -1
		-1 0 0
		0 0 1
		1 0 0
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_arm_ik_L_pointConstraint1" -p "_shape_arm_ik_L";
	rename -uid "4A341065-4E08-FF2B-B0B7-6885A4AA23E9";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_digitsW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" -1.1102230246251565e-16 1.7763568394002505e-15 -1.7763568394002505e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_ik_L_aimConstraint1" -p "_shape_arm_ik_L";
	rename -uid "A1CE96E6-4317-C722-F640-2491978300C3";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 1 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 92.380493510736926 8.9477225291287336e-15 9.3274199298569263e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_ctrls_ik_offset_L" -p "tpl_arm_digits";
	rename -uid "9BD04EAF-46E9-38C2-9B9B-77A173CDAB41";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.ik_offset";
createNode pointConstraint -n "_shape_arm_ctrls_ik_offset_L_pointConstraint1" -p "_shape_arm_ctrls_ik_offset_L";
	rename -uid "DA22C001-49C1-4969-231F-E890D2268B4C";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_digitsW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" -1.1102230246251565e-16 1.7763568394002505e-15 -1.7763568394002505e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_ctrls_ik_offset_L_aimConstraint1" -p "_shape_arm_ctrls_ik_offset_L";
	rename -uid "F04B09A4-48B2-B4CB-436A-0DB65887EC28";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 1 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 92.380493510736926 8.9477225291287336e-15 9.3274199298569263e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_arm_heel" -p "tpl_arm_limb3";
	rename -uid "5EB46429-4BFD-FBCD-92A4-ED97D4653814";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	setAttr ".v" no;
	setAttr ".t" -type "double3" -1.0830163263593484e-17 1.1102230246251565e-16 4.4408920985006262e-16 ;
	setAttr ".gem_template" -type "string" "heel";
createNode transform -n "_shape_arm_limb3_L" -p "tpl_arm_limb3";
	rename -uid "0B9C5EF6-451F-B58E-9DDE-DE9435F6DEB5";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.limb3";
createNode transform -n "shp_arm_limb3_L" -p "_shape_arm_limb3_L";
	rename -uid "0F4625AB-4AFD-E64A-55D1-05ABFDB13D22";
	setAttr ".t" -type "double3" 4.4408920985006262e-16 8.8817841970012523e-16 3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" -3.9090164039309796 0 0 ;
	setAttr ".s" -type "double3" 0.81828745282200233 0.81828745282199833 0.81828745282200643 ;
createNode nurbsCurve -n "circleShape" -p "shp_arm_limb3_L";
	rename -uid "42490D0E-43D3-BE85-B21F-11B0A70C1D88";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 -1.1106657245742172e-16 -0.53033015584183363
		-8.5566050118993011e-17 -9.7615667323108703e-17 -0.75000015700342215
		-0.53033015584183307 -1.1106657245742172e-16 -0.53033015584183363
		-0.7500001570034216 -1.4353993112490525e-16 -7.9149099434582574e-16
		-0.53033015584183307 -1.7601328979238882e-16 0.53033015584183252
		-2.2598967191885318e-16 -1.8946419492670184e-16 0.75000015700342104
		0.53033015584183307 -1.7601328979238882e-16 0.53033015584183252
		0.7500001570034216 -1.435399311249053e-16 -1.7133317877610043e-16
		0.53033015584183307 -1.1106657245742172e-16 -0.53033015584183363
		-8.5566050118993011e-17 -9.7615667323108703e-17 -0.75000015700342215
		-0.53033015584183307 -1.1106657245742172e-16 -0.53033015584183363
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_limb3_L_pointConstraint1" -p "_shape_arm_limb3_L";
	rename -uid "EC93A26E-4937-3993-72F7-EA9D76CF8C60";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 8.8817841970012523e-16 -1.7763568394002505e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_limb3_L_aimConstraint1" -p "_shape_arm_limb3_L";
	rename -uid "31D60D53-479F-3F1C-2F7D-6FBD6E71A31D";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_digitsW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 2.3804935107369372 -1.8590426829077273e-16 8.9477225291288425e-15 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_fingers" -p "tpl_arm_limb3";
	rename -uid "5F102E70-4886-C296-682F-028C6D1DA789";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "nts" -ln "notes" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr -l on ".tx";
	setAttr -l on ".ty";
	setAttr -l on ".tz";
	setAttr -l on ".rx";
	setAttr -l on ".ry";
	setAttr -l on ".rz";
	setAttr -l on ".sx";
	setAttr -l on ".sy";
	setAttr -l on ".sz";
	setAttr ".ds" 2;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "fingers";
	setAttr ".gem_module" -type "string" "core.group";
	setAttr ".gem_template" -type "string" "[template]\ndesc: pass through template to add new group\n\nopts:\n  main:\n    value: off";
	setAttr ".nts" -type "string" "[mod]\n# -- fingers vis group\n\ngroup:\n nodes:\n  - fingers.L:::ctrls\n tag: vis.fingers\n";
	setAttr ".gem_hook" -type "string" "fingers.L::hooks.group";
createNode joint -n "tpl_thumb" -p "tpl_fingers";
	rename -uid "CAF367BA-4E4F-4A27-96AF-3683F9334AD0";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -k true -sn "gem_opt_meta" -ln "gem_opt_meta" -dv 1 -min 0 -max 
		1 -at "bool";
	addAttr -ci true -k true -sn "gem_opt_shear" -ln "gem_opt_shear" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_opt_shear_values" -ln "gem_opt_shear_values" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.075394570827484131 0.091621018946170807 -0.041442569345235825 ;
	setAttr ".r" -type "double3" -42.532537706902644 24.839673978708166 287.84787082969871 ;
	setAttr ".ssc" no;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "thumb";
	setAttr ".gem_module" -type "string" "digit.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy digit from ttRig3\n\nstructure:\n  chain: /*\n  base: chain[:-1]\n  tip: chain[1:]\n\nopts:\n  merge:\n    value: 2\n\n  meta:\n    value: on\n  target_parent:\n    value: hooks.digits\n    \n  orient:\n    value: 1\n    enum: {0: copy, 1: auto}\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: z";
	setAttr -k on ".gem_opt_meta" no;
	setAttr -k on ".gem_opt_shear" yes;
	setAttr ".gem_opt_shear_values" -type "string" "[0, 0.5, 1]";
	setAttr ".ui_expanded" no;
	setAttr ".gem_hook" -type "string" "thumb.L::hooks.0";
	setAttr ".gem_dag_ctrls" -type "string" "thumb.L::ctrls.0";
	setAttr ".gem_dag_skin" -type "string" "thumb.L::skin.0";
createNode joint -n "tpl_thumb_chain1" -p "tpl_thumb";
	rename -uid "AB74C661-48F0-7521-D6D9-9EB85B248095";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.090904280543327332 0.39920571446418762 0.034428808838129044 ;
	setAttr ".r" -type "double3" -12.307012799296086 38.81551824734624 18.950791913694658 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "thumb.L::hooks.1";
	setAttr ".gem_dag_ctrls" -type "string" "thumb.L::ctrls.1";
	setAttr ".gem_dag_skin" -type "string" "thumb.L::skin.1";
createNode joint -n "tpl_thumb_chain2" -p "tpl_thumb_chain1";
	rename -uid "F0F5646B-40F0-3812-1A70-96B6A18069D6";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.31755572557449341 -0.010202783159911633 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "thumb.L::hooks.2";
	setAttr ".gem_dag_ctrls" -type "string" "thumb.L::ctrls.2";
	setAttr ".gem_dag_skin" -type "string" "thumb.L::hooks.last";
createNode joint -n "tpl_thumb_tip" -p "tpl_thumb_chain2";
	rename -uid "247D9856-4D1E-C117-DAD2-83855B48C721";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr ".t" -type "double3" 0 0.34668675065040588 -0.047342102974653244 ;
	setAttr ".gem_hook" -type "string" "thumb.L::hooks.tip";
createNode transform -n "_shape_thumb_2_L" -p "tpl_thumb_chain2";
	rename -uid "96E45E8D-4324-60D3-DF86-D7A1F43C5BC1";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "thumb.L::ctrls.2";
createNode transform -n "shp_thumb_2_L" -p "_shape_thumb_2_L";
	rename -uid "99322549-4DBA-5A8F-1715-BBA23C2B2299";
	setAttr ".t" -type "double3" -1.7763568394002505e-15 -0.065257385373104881 0.02367105148732529 ;
	setAttr ".s" -type "double3" 0.11095548421144485 0.081602327525615692 0.14035029709339142 ;
createNode nurbsCurve -n "cubeShape" -p "shp_thumb_2_L";
	rename -uid "39C84544-4497-BEC0-91DD-C295B30ACE34";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 20;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.53104925 0.6002931 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "pink";
createNode pointConstraint -n "_shape_thumb_2_L_pointConstraint1" -p "_shape_thumb_2_L";
	rename -uid "84DCBFF4-4C7E-7ABA-1E6E-5187CD9823D9";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_thumb_chain2W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_thumb_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 0.17334337532520294 -0.02367105148732751 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_thumb_1_L" -p "tpl_thumb_chain1";
	rename -uid "7B1EAB01-462A-4F0A-C82A-A6848FA33EEB";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "thumb.L::ctrls.1";
createNode transform -n "shp_thumb_1_L" -p "_shape_thumb_1_L";
	rename -uid "5F014D73-46E3-C066-A978-E2B2591689DF";
	setAttr ".t" -type "double3" 2.6645352591003757e-15 -0.020020171999936665 0.0051013915799518195 ;
	setAttr ".s" -type "double3" 0.15092600882053375 0.14544469118118286 0.17430286109447479 ;
createNode nurbsCurve -n "cubeShape" -p "shp_thumb_1_L";
	rename -uid "FF2CE924-4590-82BB-D6E5-E0ADF7D9D13E";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 21;
	setAttr ".ovrgb" -type "float3" 0.70933133 0.16223767 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.59868933128971646 -0.5 0.61769107389357492
		-0.59868933128971624 -0.5 0.61769107389357492
		-0.59868933128971624 -0.5 -0.61769107389357492
		0.59868933128971646 -0.5 -0.61769107389357492
		0.59868933128971646 -0.5 0.61769107389357492
		0.51819885075602146 0.5 0.56269740573660765
		-0.51819557434507935 0.5 0.56269740573660765
		-0.59868933128971624 -0.5 0.61769107389357492
		-0.59868933128971624 -0.5 -0.61769107389357492
		-0.51819557434507935 0.5 -0.56269740573660731
		-0.51819557434507935 0.5 0.56269740573660765
		0.51819885075602146 0.5 0.56269740573660765
		0.51819885075602146 0.5 -0.56269740573660731
		-0.51819557434507935 0.5 -0.56269740573660731
		-0.59868933128971624 -0.5 -0.61769107389357492
		0.59868933128971646 -0.5 -0.61769107389357492
		0.51819885075602146 0.5 -0.56269740573660731
		;
	setAttr ".gem_color" -type "string" "palevioletred";
createNode pointConstraint -n "_shape_thumb_1_L_pointConstraint1" -p "_shape_thumb_1_L";
	rename -uid "8C839706-440B-5344-0234-2CA96612065B";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_thumb_chain1W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_thumb_chain2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 0.15877786278724848 -0.0051013915799571485 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_thumb_0_L" -p "tpl_thumb";
	rename -uid "E0156DAD-4A45-0EF9-1783-40B657E14BC1";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "thumb.L::ctrls.0";
createNode transform -n "shp_thumb_0_L" -p "_shape_thumb_0_L";
	rename -uid "0C39D778-44FE-45CC-F714-4A9E3299BFE6";
	setAttr ".t" -type "double3" 0.021852139383548463 0.063567981123922479 -0.015913071692922109 ;
	setAttr ".r" -type "double3" 0 0 13.453158040484134 ;
	setAttr ".s" -type "double3" 0.32858550548553467 0.20002870261669159 0.45878863334655762 ;
createNode nurbsCurve -n "cubeShape" -p "shp_thumb_0_L";
	rename -uid "D1D70867-4378-98FE-E540-18B33199DCA9";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 9;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.0036655408 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.4547658299737915 -0.5 0.44996904291085804
		-0.45852129328853342 -0.5 0.44996904291085804
		-0.45852129328853342 -0.5 -0.45166072078999175
		0.4547658299737915 -0.5 -0.45166072078999175
		0.4547658299737915 -0.5 0.44996904291085804
		0.40266981720253409 0.50000000000000011 0.40267133792484056
		-0.40266654079159275 0.50000000000000011 0.40267133792484056
		-0.45852129328853342 -0.5 0.44996904291085804
		-0.51790596750535545 -0.5 -0.45166072078999175
		-0.40266654079159275 0.50000000000000011 -0.40267133792484172
		-0.40266654079159275 0.50000000000000011 0.40267133792484056
		0.40266981720253409 0.50000000000000011 0.40267133792484056
		0.40266981720253409 0.50000000000000011 -0.40267133792484172
		-0.40266654079159275 0.50000000000000011 -0.40267133792484172
		-0.51790596750535545 -0.5 -0.45166072078999175
		0.4547658299737915 -0.5 -0.45166072078999175
		0.40266981720253409 0.50000000000000011 -0.40267133792484172
		;
	setAttr ".gem_color" -type "string" "deeppink";
createNode pointConstraint -n "_shape_thumb_0_L_pointConstraint1" -p "_shape_thumb_0_L";
	rename -uid "781EFC52-44C7-195C-9560-A4A391DFB872";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_thumbW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_thumb_chain1W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.045452140271661556 0.19960285723209381 0.01721440441906541 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode joint -n "tpl_point" -p "tpl_fingers";
	rename -uid "62459EC1-459F-08B3-7E9B-C0BC4A9D27B8";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -k true -sn "gem_opt_shear" -ln "gem_opt_shear" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_opt_shear_values" -ln "gem_opt_shear_values" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.16321447491645813 0.15339542925357819 -0.0068430802784860134 ;
	setAttr ".ssc" no;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "point";
	setAttr ".gem_module" -type "string" "digit.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy digit from ttRig3\n\nstructure:\n  chain: /*\n  base: chain[:-1]\n  tip: chain[1:]\n\nopts:\n  merge:\n    value: 2\n\n  meta:\n    value: on\n  target_parent:\n    value: hooks.digits\n    \n  orient:\n    value: 1\n    enum: {0: copy, 1: auto}\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: z";
	setAttr -k on ".gem_opt_shear" yes;
	setAttr ".gem_opt_shear_values" -type "string" "[0, 0.7, 1, 1]";
	setAttr ".ui_expanded" no;
	setAttr ".gem_hook" -type "string" "point.L::hooks.0";
	setAttr ".gem_dag_ctrls" -type "string" "point.L::ctrls.0";
	setAttr ".gem_dag_skin" -type "string" "point.L::skin.0";
createNode joint -n "tpl_point_chain1" -p "tpl_point";
	rename -uid "89FA8189-4E11-BDDF-C4CF-A9921753F905";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.042191512882709503 0.5850517749786377 0.00066543964203447104 ;
	setAttr ".r" -type "double3" 0.081274352637509456 2.7789005380605518 0.62604750874863346 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "point.L::hooks.1";
	setAttr ".gem_dag_ctrls" -type "string" "point.L::ctrls.1";
	setAttr ".gem_dag_skin" -type "string" "point.L::skin.1";
createNode joint -n "tpl_point_chain2" -p "tpl_point_chain1";
	rename -uid "25A1ED16-4E51-848A-0AF7-518FC6C41CA1";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.36730983853340149 -0.013279331848025322 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "point.L::hooks.2";
	setAttr ".gem_dag_ctrls" -type "string" "point.L::ctrls.2";
	setAttr ".gem_dag_skin" -type "string" "point.L::skin.2";
createNode joint -n "tpl_point_chain3" -p "tpl_point_chain2";
	rename -uid "FBF140CA-4A67-0CD2-6EBD-13A55B2EEFE7";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.22579598426818848 -0.033828489482402802 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "point.L::hooks.3";
	setAttr ".gem_dag_ctrls" -type "string" "point.L::ctrls.3";
	setAttr ".gem_dag_skin" -type "string" "point.L::hooks.last";
createNode joint -n "tpl_point_tip" -p "tpl_point_chain3";
	rename -uid "86964A2A-4F01-DA58-8FBD-C58AF9077504";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr ".t" -type "double3" -0.00016882974887266755 0.21511641144752502 -0.0082820160314440727 ;
	setAttr ".gem_hook" -type "string" "point.L::hooks.tip";
createNode transform -n "_shape_point_3_L" -p "tpl_point_chain3";
	rename -uid "07D98CD2-4043-2C0F-56CB-0B971A127C08";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "point.L::ctrls.3";
createNode transform -n "shp_point_3_L" -p "_shape_point_3_L";
	rename -uid "22A14979-43FF-9170-6C39-9D95665C5E40";
	setAttr ".t" -type "double3" 8.4414874436611331e-05 0.00044579803944433394 0.00414100801572026 ;
	setAttr ".s" -type "double3" 0.09766659140586853 0.082228310406208038 0.15016922354698181 ;
createNode nurbsCurve -n "cubeShape" -p "shp_point_3_L";
	rename -uid "AADBB3FC-4D5A-4C22-754F-36B8E96C9671";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 20;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.47209471 0.53715318 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "lightpink";
createNode pointConstraint -n "_shape_point_3_L_pointConstraint1" -p "_shape_point_3_L";
	rename -uid "9117E4F8-4725-9A96-B583-9890D4A3F6B3";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_point_chain3W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_point_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -8.4414874436111731e-05 0.10755820572376251 -0.0041410080157220364 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_point_2_L" -p "tpl_point_chain2";
	rename -uid "40FE2E21-4C22-B632-3DEC-BE9EB9C5D5EB";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "point.L::ctrls.2";
createNode transform -n "shp_point_2_L" -p "_shape_point_2_L";
	rename -uid "47338D52-4BDC-421D-C148-8EBAAEB55EFD";
	setAttr ".t" -type "double3" -8.2074492780970232e-06 -0.0067068788600659346 0.016914244741201401 ;
	setAttr ".r" -type "double3" 0 0 0.0044283574094573968 ;
	setAttr ".s" -type "double3" 0.11009829491376878 0.11175348609685896 0.17751923203468323 ;
createNode nurbsCurve -n "cubeShape" -p "shp_point_2_L";
	rename -uid "2521C198-4981-CB03-2E4F-BFBEF2325E57";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 21;
	setAttr ".ovrgb" -type "float3" 0.70933133 0.16223767 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.70409148444202208 -0.50000000000000111 0.66580650870882541
		-0.70409148444202208 -0.50000000000000111 0.66580650870882541
		-0.70409148444202208 -0.50000000000000111 -0.66580650870882541
		0.70409148444202208 -0.50000000000000111 -0.66580650870882541
		0.70409148444202208 -0.50000000000000111 0.66580650870882541
		0.66898605731702121 0.49999999999999811 0.62929877199597384
		-0.66898278090608265 0.49999999999999811 0.62929877199597384
		-0.70409148444202208 -0.50000000000000111 0.66580650870882541
		-0.70409148444202208 -0.50000000000000111 -0.66580650870882541
		-0.66898278090608265 0.49999999999999811 -0.62929877199597606
		-0.66898278090608265 0.49999999999999811 0.62929877199597384
		0.66898605731702121 0.49999999999999811 0.62929877199597384
		0.66898605731702121 0.49999999999999811 -0.62929877199597606
		-0.66898278090608265 0.49999999999999811 -0.62929877199597606
		-0.70409148444202208 -0.50000000000000111 -0.66580650870882541
		0.70409148444202208 -0.50000000000000111 -0.66580650870882541
		0.66898605731702121 0.49999999999999811 -0.62929877199597606
		;
	setAttr ".gem_color" -type "string" "palevioletred";
createNode pointConstraint -n "_shape_point_2_L_pointConstraint1" -p "_shape_point_2_L";
	rename -uid "162F38F2-47D8-2C71-1E41-C6B600E10BBE";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_point_chain2W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_point_chain3W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 1.6653345369377348e-16 0.11289799213409601 -0.016914244741201401 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_point_1_L" -p "tpl_point_chain1";
	rename -uid "8F9EDA16-496D-2640-CA68-9CA51EC07500";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "point.L::ctrls.1";
createNode transform -n "shp_point_1_L" -p "_shape_point_1_L";
	rename -uid "369537B2-4EA8-0F6A-9C07-02BE3E53E258";
	setAttr ".t" -type "double3" -1.4993728722767496e-05 -0.011454925593826104 0.0066396659240055556 ;
	setAttr ".r" -type "double3" 0 0 0.0049888351011043311 ;
	setAttr ".s" -type "double3" 0.082445204257965116 0.22957381606101987 0.24903316795825961 ;
createNode nurbsCurve -n "cubeShape" -p "shp_point_1_L";
	rename -uid "123E2AE0-430C-EA5D-9088-248385A025BC";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 9;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.0036655408 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "deeppink";
createNode pointConstraint -n "_shape_point_1_L_pointConstraint1" -p "_shape_point_1_L";
	rename -uid "CCBF373E-4B2C-1C50-8673-EDA430E50F83";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_point_chain1W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_point_chain2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 1.6653345369377348e-16 0.18365491926670163 -0.0066396659240144373 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_point_0_L" -p "tpl_point";
	rename -uid "EA1E8203-4740-3D99-A171-2D9FCEC9CFD3";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "point.L::ctrls.0";
createNode transform -n "shp_point_0_L" -p "_shape_point_0_L";
	rename -uid "797CF87A-4E4E-D468-C91D-BFA45F667296";
	setAttr ".t" -type "double3" -0.059639690800617373 -0.24631339692824206 -0.059429915428561131 ;
	setAttr ".r" -type "double3" -79.072480746594394 16.19530113989228 -7.0377193171432735 ;
	setAttr ".s" -type "double3" 0.088107272982597351 0.46443995833396934 0.088107272982597407 ;
createNode nurbsCurve -n "cubeShape" -p "shp_point_0_L";
	rename -uid "709D6D2A-4E05-A992-BC2B-E1A97E8FA6F2";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 30;
	setAttr ".ovrgb" -type "float3" 0.32225022 0.027517317 0.60681796 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "darkorchid";
createNode pointConstraint -n "_shape_point_0_L_pointConstraint1" -p "_shape_point_0_L";
	rename -uid "17A75F96-4A46-686F-E675-089FD598E9B2";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_pointW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_point_chain1W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0.021095756441354641 0.29252588748932062 0.00033271982101723552 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode joint -n "tpl_middle" -p "tpl_fingers";
	rename -uid "A368BB40-4742-E950-4D5F-5095B579B35E";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -k true -sn "gem_opt_shear" -ln "gem_opt_shear" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_opt_shear_values" -ln "gem_opt_shear_values" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.034925512969493866 0.16038317978382111 -0.0046792118810117245 ;
	setAttr ".ssc" no;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "middle";
	setAttr ".gem_module" -type "string" "digit.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy digit from ttRig3\n\nstructure:\n  chain: /*\n  base: chain[:-1]\n  tip: chain[1:]\n\nopts:\n  merge:\n    value: 2\n\n  meta:\n    value: on\n  target_parent:\n    value: hooks.digits\n    \n  orient:\n    value: 1\n    enum: {0: copy, 1: auto}\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: z";
	setAttr -k on ".gem_opt_shear" yes;
	setAttr ".gem_opt_shear_values" -type "string" "[0, 0.7, 1, 1]";
	setAttr ".ui_expanded" no;
	setAttr ".gem_hook" -type "string" "middle.L::hooks.0";
	setAttr ".gem_dag_ctrls" -type "string" "middle.L::ctrls.0";
	setAttr ".gem_dag_skin" -type "string" "middle.L::skin.0";
createNode joint -n "tpl_middle_chain1" -p "tpl_middle";
	rename -uid "09E1FEEA-401F-1E67-7F6C-3A8F05DC31BF";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.0025704675354063511 0.57962781190872192 0.019568376243114471 ;
	setAttr ".r" -type "double3" 0.0079940991281194328 1.6108810107059668 1.9950509717034828 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "middle.L::hooks.1";
	setAttr ".gem_dag_ctrls" -type "string" "middle.L::ctrls.1";
	setAttr ".gem_dag_skin" -type "string" "middle.L::skin.1";
createNode joint -n "tpl_middle_chain2" -p "tpl_middle_chain1";
	rename -uid "1C12D79B-4FD3-5A64-B2B1-9584D354E9B8";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.40068218111991882 -0.010029817000031471 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "middle.L::hooks.2";
	setAttr ".gem_dag_ctrls" -type "string" "middle.L::ctrls.2";
	setAttr ".gem_dag_skin" -type "string" "middle.L::skin.2";
createNode joint -n "tpl_middle_chain3" -p "tpl_middle_chain2";
	rename -uid "EA033B6F-473B-0287-B425-51A92CE89641";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.24396520853042603 -0.025934971868991852 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "middle.L::hooks.3";
	setAttr ".gem_dag_ctrls" -type "string" "middle.L::ctrls.3";
	setAttr ".gem_dag_skin" -type "string" "middle.L::hooks.last";
createNode joint -n "tpl_middle_tip" -p "tpl_middle_chain3";
	rename -uid "A5FD6506-497F-1291-8658-C2A03A5FC326";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr ".t" -type "double3" 0 0.24035823345184326 -0.03122563473880291 ;
	setAttr ".gem_hook" -type "string" "middle.L::hooks.tip";
createNode transform -n "_shape_middle_3_L" -p "tpl_middle_chain3";
	rename -uid "3E023108-42BC-007D-5FCE-06A05259048D";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "middle.L::ctrls.3";
createNode transform -n "shp_middle_3_L" -p "_shape_middle_3_L";
	rename -uid "9383C7B4-4CF5-37FD-77F9-14B6B0E46C95";
	setAttr ".t" -type "double3" 1.6653345369377348e-16 -0.0063466131687208716 0.015612817369401455 ;
	setAttr ".s" -type "double3" 0.09766659140586853 0.082228310406208024 0.16347301006317136 ;
createNode nurbsCurve -n "cubeShape" -p "shp_middle_3_L";
	rename -uid "2AE0C75B-4306-C799-ACFD-4786A854BDB5";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 20;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.47209471 0.53715318 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "lightpink";
createNode pointConstraint -n "_shape_middle_3_L_pointConstraint1" -p "_shape_middle_3_L";
	rename -uid "DB868921-4830-54DE-3876-A8B9D44A25EA";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_middle_chain3W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_middle_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -1.1102230246251565e-16 0.12017911672592252 -0.015612817369403231 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_middle_2_L" -p "tpl_middle_chain2";
	rename -uid "A4887283-4F2B-7306-0E09-ED8B8DE825EC";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "middle.L::ctrls.2";
createNode transform -n "shp_middle_2_L" -p "_shape_middle_2_L";
	rename -uid "B2ED6BA1-4550-FF2E-AC40-47A1786934F3";
	setAttr ".t" -type "double3" 0.00012625843979507945 0.00053415960282165997 0.013092641142590011 ;
	setAttr ".r" -type "double3" 0.058529614064224439 3.01585364543109e-05 -0.059045547436360306 ;
	setAttr ".s" -type "double3" 0.11009829491376878 0.11175348609685895 0.19324600696563723 ;
createNode nurbsCurve -n "cubeShape" -p "shp_middle_2_L";
	rename -uid "8D511A0D-496C-AD62-A05C-0A9E7860E6B9";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 21;
	setAttr ".ovrgb" -type "float3" 0.70933133 0.16223767 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "palevioletred";
createNode pointConstraint -n "_shape_middle_2_L_pointConstraint1" -p "_shape_middle_2_L";
	rename -uid "8ABA9E92-4429-B187-0E55-E981CCC61334";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_middle_chain2W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_middle_chain3W1" -dv 1 -min 0 
		-at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -1.1102230246251565e-16 0.12198260426521568 -0.012967485934495926 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_middle_1_L" -p "tpl_middle_chain1";
	rename -uid "A2888971-4371-0514-722E-ADAE1AD84004";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "middle.L::ctrls.1";
createNode transform -n "shp_middle_1_L" -p "_shape_middle_1_L";
	rename -uid "0CC5ACF2-47E6-EBA2-8ED6-D5B8778BCABE";
	setAttr ".t" -type "double3" -1.2222092641123172e-05 -0.028141161029974882 0.0048660251940386701 ;
	setAttr ".r" -type "double3" -0.049537667924125707 1.7579965868304267e-06 0.0040666338493630296 ;
	setAttr ".s" -type "double3" 0.082445204257965157 0.22957381606101984 0.27109548449516263 ;
createNode nurbsCurve -n "cubeShape" -p "shp_middle_1_L";
	rename -uid "012AFD84-49B0-BCFF-6E50-93899A385BA7";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 9;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.0036655408 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "deeppink";
createNode pointConstraint -n "_shape_middle_1_L_pointConstraint1" -p "_shape_middle_1_L";
	rename -uid "038F5C89-4843-AC0C-717C-2E93DBD1DC71";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_middle_chain1W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_middle_chain2W1" -dv 1 -min 0 
		-at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 2.7755575615628914e-17 0.20034109055995852 -0.0050149085000157356 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_middle_0_L" -p "tpl_middle";
	rename -uid "82AFC1A8-4F16-58D3-48F0-ADBF3A4D264D";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "middle.L::ctrls.0";
createNode transform -n "shp_middle_0_L" -p "_shape_middle_0_L";
	rename -uid "583185B5-4CEB-52D9-E111-94AF8BD5D2F9";
	setAttr ".t" -type "double3" -0.0066508910481480887 -0.26094551506100849 -0.026571085844476983 ;
	setAttr ".r" -type "double3" -81.385222171339109 0.058740642381967481 -0.77986838654548551 ;
	setAttr ".s" -type "double3" 0.088107272982597407 0.42538642883300737 0.088107272982597309 ;
createNode nurbsCurve -n "cubeShape" -p "shp_middle_0_L";
	rename -uid "8F705279-4DE8-1B43-1023-AF82E5ECE59C";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 30;
	setAttr ".ovrgb" -type "float3" 0.32225022 0.027517317 0.60681796 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "darkorchid";
createNode pointConstraint -n "_shape_middle_0_L_pointConstraint1" -p "_shape_middle_0_L";
	rename -uid "750CA5F9-4237-BF3E-FE8B-CB8982846191";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_middleW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_middle_chain1W1" -dv 1 -min 0 
		-at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.0012852337677032866 0.28981390595436451 0.009784188121553683 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode joint -n "tpl_ring" -p "tpl_fingers";
	rename -uid "FB1D50FD-45AD-4BF3-23C5-08AE131F9A47";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "gem_opt_shear" -ln "gem_opt_shear" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_opt_shear_values" -ln "gem_opt_shear_values" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.09630768746137619 0.15841147303581238 -0.0068962196819484234 ;
	setAttr ".ssc" no;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "ring";
	setAttr ".gem_module" -type "string" "digit.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy digit from ttRig3\n\nstructure:\n  chain: /*\n  base: chain[:-1]\n  tip: chain[1:]\n\nopts:\n  meta:\n    value: on\n  shear:\n    value: off\n  shear_values:\n    value: ''\n    yaml: on\n  target_parent:\n    value: hooks.digits\n  target_weights:\n    value: ''\n    yaml: on\n\n  do_pose:\n    value: off\n  add_nodes:\n    value: ''\n    yaml: on\n  parent_scale:\n    value: off\n\n  rotate_order:\n    value: 0\n    enum: {0: xyz, 1: yzx, 2: zxy, 3: xzy, 4: yxz, 5: zyx, 6: auto}\n\n  orient:\n    value: 0\n    enum: {0: copy, 1: auto}\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: z\n  up_dir:\n    value: 0\n    enum: {0: auto, 1: +x, 2: -x, 3: +y, 4: -y, 5: +z, 6: -z}\n  up_auto:\n    value: 0\n    enum: {0: average, 1: each, 2: first, 3: last}";
	setAttr -k on ".gem_opt_shear" yes;
	setAttr -k on ".gem_opt_shear_values" -type "string" "[0, 0.7, 1, 1]";
	setAttr ".ui_expanded" no;
	setAttr ".gem_hook" -type "string" "ring.L::hooks.0";
	setAttr ".gem_dag_ctrls" -type "string" "ring.L::ctrls.0";
	setAttr ".gem_dag_skin" -type "string" "ring.L::skin.0";
createNode joint -n "tpl_ring_chain1" -p "tpl_ring";
	rename -uid "C4412FD2-4E99-7B99-7C84-87AE18BB2ABC";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.04812905564904213 0.56068587303161621 0.014399423263967037 ;
	setAttr ".r" -type "double3" -0.022412304088117549 -0.86233092489925989 3.3 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "ring.L::hooks.1";
	setAttr ".gem_dag_ctrls" -type "string" "ring.L::ctrls.1";
	setAttr ".gem_dag_skin" -type "string" "ring.L::skin.1";
createNode joint -n "tpl_ring_chain2" -p "tpl_ring_chain1";
	rename -uid "82D71C23-4014-9A25-6B3A-8FB83A0D5474";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.38028660416603088 -0.018591420724987984 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "ring.L::hooks.2";
	setAttr ".gem_dag_ctrls" -type "string" "ring.L::ctrls.2";
	setAttr ".gem_dag_skin" -type "string" "ring.L::skin.2";
createNode joint -n "tpl_ring_chain3" -p "tpl_ring_chain2";
	rename -uid "828EE379-4BFA-C4C9-F9F1-D69FC6BBB242";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.21505835652351379 -0.020967422053217888 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "ring.L::hooks.3";
	setAttr ".gem_dag_ctrls" -type "string" "ring.L::ctrls.3";
	setAttr ".gem_dag_skin" -type "string" "ring.L::hooks.last";
createNode joint -n "tpl_ring_tip" -p "tpl_ring_chain3";
	rename -uid "507CAE83-4D1D-CF64-74A7-FB85AA9762B2";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr ".t" -type "double3" 0 0.21335469186306 -0.022175882011651993 ;
	setAttr ".gem_hook" -type "string" "ring.L::hooks.tip";
createNode transform -n "_shape_ring_3_L" -p "tpl_ring_chain3";
	rename -uid "4444CDD5-43F4-D2F3-8A55-36BEDF2485AA";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "ring.L::ctrls.3";
createNode transform -n "shp_ring_3_L" -p "_shape_ring_3_L";
	rename -uid "D37C16A8-40A0-023D-7646-768533359E9E";
	setAttr ".t" -type "double3" 4.9960036108132044e-16 0.0068778673682130531 0.0031473869602098858 ;
	setAttr ".r" -type "double3" -3.9999999999999836 0 0 ;
	setAttr ".s" -type "double3" 0.097666591405868461 0.082228310406207997 0.16347301006317119 ;
createNode nurbsCurve -n "cubeShape" -p "shp_ring_3_L";
	rename -uid "47A6F1A0-40D5-E450-E78A-2E95DD80DAB2";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 20;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.47209471 0.53715318 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "lightpink";
createNode pointConstraint -n "_shape_ring_3_L_pointConstraint1" -p "_shape_ring_3_L";
	rename -uid "55C70B23-40A8-BA8B-71A3-FDA2A1A915EC";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_ring_chain3W0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_ring_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 0.10667734593152911 -0.011087941005825996 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_ring_2_L" -p "tpl_ring_chain2";
	rename -uid "B5E8D2AD-4A22-2C45-A505-A88AEFA36551";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "ring.L::ctrls.2";
createNode transform -n "shp_ring_2_L" -p "_shape_ring_2_L";
	rename -uid "7058C10B-4D36-36B3-90AA-A391A88E01D7";
	setAttr ".t" -type "double3" 0.00012625843979452434 0.014917319557793185 0.0063330165969226471 ;
	setAttr ".r" -type "double3" -1.941469324749697 -0.0020305193590488147 -0.059010631026845721 ;
	setAttr ".s" -type "double3" 0.11009829491376869 0.11175348609685887 0.19324600696563721 ;
createNode nurbsCurve -n "cubeShape" -p "shp_ring_2_L";
	rename -uid "641A0A5E-4EAE-17B2-3DB5-9F815B3F068D";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 21;
	setAttr ".ovrgb" -type "float3" 0.70933133 0.16223767 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "palevioletred";
createNode pointConstraint -n "_shape_ring_2_L_pointConstraint1" -p "_shape_ring_2_L";
	rename -uid "10C12058-4830-3B6D-3F25-C48235FEBE9C";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_ring_chain2W0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_ring_chain3W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 5.5511151231257827e-17 0.10752917826175779 -0.01048371102661072 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_ring_1_L" -p "tpl_ring_chain1";
	rename -uid "E843D4E1-4DD0-555D-3CB5-5C9F6FFF2360";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "ring.L::ctrls.1";
createNode transform -n "shp_ring_1_L" -p "_shape_ring_1_L";
	rename -uid "3F313062-4897-8FF3-7BA6-348D96A12F63";
	setAttr ".t" -type "double3" -1.2222092641289706e-05 -0.017943372553030024 0.0091468270565115972 ;
	setAttr ".r" -type "double3" -0.049537667924114133 1.757996587866453e-06 0.0040666338493672519 ;
	setAttr ".s" -type "double3" 0.082445204257965088 0.22957381606101987 0.27109548449516285 ;
createNode nurbsCurve -n "cubeShape" -p "shp_ring_1_L";
	rename -uid "5CF36BEE-4166-350A-A5E9-61AB8670DEA3";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 9;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.0036655408 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "deeppink";
createNode pointConstraint -n "_shape_ring_1_L_pointConstraint1" -p "_shape_ring_1_L";
	rename -uid "EE22E517-4345-D100-F531-799BC410C67C";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_ring_chain1W0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_ring_chain2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 0.19014330208301455 -0.0092957103624922155 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_ring_0_L" -p "tpl_ring";
	rename -uid "83465284-4501-DA85-162E-04BBA52046A7";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "ring.L::ctrls.0";
createNode transform -n "shp_ring_0_L" -p "_shape_ring_0_L";
	rename -uid "F3C06467-4CC0-577C-C18C-BDB4EE6B8DF5";
	setAttr ".t" -type "double3" 0.016174596908554606 -0.25918192371696502 -0.0040020075991531456 ;
	setAttr ".r" -type "double3" -81.386963463201269 -0.18351331135814372 0.81923173602326216 ;
	setAttr ".s" -type "double3" 0.088107272982597365 0.39340993762016269 0.088107272982597268 ;
createNode nurbsCurve -n "cubeShape" -p "shp_ring_0_L";
	rename -uid "A5062D69-4659-A4AD-C469-05927F895C9A";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 30;
	setAttr ".ovrgb" -type "float3" 0.32225022 0.027517317 0.60681796 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "darkorchid";
createNode pointConstraint -n "_shape_ring_0_L_pointConstraint1" -p "_shape_ring_0_L";
	rename -uid "22EACA16-4E8D-DAA9-8685-2E860509DE24";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_ringW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_ring_chain1W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.024064527824521231 0.28034293651580988 0.0071997116319817422 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode joint -n "tpl_pinky" -p "tpl_fingers";
	rename -uid "F8FC4676-4DE7-836F-0891-F3ACE68F671B";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "nts" -ln "notes" -dt "string";
	addAttr -ci true -k true -sn "gem_opt_shear" -ln "gem_opt_shear" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_opt_shear_values" -ln "gem_opt_shear_values" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.21040064096450806 0.14568910002708435 -0.018877491354942322 ;
	setAttr ".ssc" no;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "pinky";
	setAttr ".gem_module" -type "string" "digit.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy digit from ttRig3\n\nstructure:\n  chain: /*\n  base: chain[:-1]\n  tip: chain[1:]\n\nopts:\n  merge:\n    value: 2\n\n  meta:\n    value: on\n  target_parent:\n    value: hooks.digits\n    \n  orient:\n    value: 1\n    enum: {0: copy, 1: auto}\n\n  aim_axis:\n    value: y\n  up_axis:\n    value: z";
	setAttr ".nts" -type "string" "[mod]\n# -- pinky cup rig\n\nconstraint:\n  type: point\n  node: ring.L::infs.0\n  targets:\n   - pinky.L::ctrls.0\n   - point.L::roots.0\n  weights: [2, 1]\n  maintain_offset: on\n\nconstraint:\n  type: point\n  node: middle.L::infs.0\n  targets:\n   - pinky.L::ctrls.0\n   - point.L::roots.0\n  weights: [1, 2]\n  maintain_offset: on\n\nconstraint:\n  type: orient\n  node: ring.L::infs.0\n  targets:\n   - pinky.L::ctrls.0\n   - point.L::roots.0\n  weights: [2, 1]\n  maintain_offset: on\n\nconstraint:\n  type: orient\n  node: middle.L::infs.0\n  targets:\n   - pinky.L::ctrls.0\n   - point.L::roots.0\n  weights: [1, 2]\n  maintain_offset: on";
	setAttr -k on ".gem_opt_shear" yes;
	setAttr ".gem_opt_shear_values" -type "string" "[0, 0.7, 1, 1]";
	setAttr ".gem_hook" -type "string" "pinky.L::hooks.0";
	setAttr ".gem_dag_ctrls" -type "string" "pinky.L::ctrls.0";
	setAttr ".gem_dag_skin" -type "string" "pinky.L::skin.0";
createNode joint -n "tpl_pinky_chain1" -p "tpl_pinky";
	rename -uid "BCFDC07D-487B-214B-CAD3-87A2BC375013";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" -0.092910870909690857 0.52848535776138306 0.0094944275915622711 ;
	setAttr ".r" -type "double3" -0.19939624191496241 -2.4547045546873085 4.6453871434359755 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "pinky.L::hooks.1";
	setAttr ".gem_dag_ctrls" -type "string" "pinky.L::ctrls.1";
	setAttr ".gem_dag_skin" -type "string" "pinky.L::skin.1";
createNode joint -n "tpl_pinky_chain2" -p "tpl_pinky_chain1";
	rename -uid "B9812CD7-4DFB-9407-3374-CF83891E96AB";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.28245300054550171 -0.015752200037240982 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "pinky.L::hooks.2";
	setAttr ".gem_dag_ctrls" -type "string" "pinky.L::ctrls.2";
	setAttr ".gem_dag_skin" -type "string" "pinky.L::skin.2";
createNode joint -n "tpl_pinky_chain3" -p "tpl_pinky_chain2";
	rename -uid "F65D39DD-40EA-0E58-4D04-A3ACDA05D134";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.1950499415397644 -0.031522680073976517 ;
	setAttr ".radi" 0.5;
	setAttr ".gem_hook" -type "string" "pinky.L::hooks.3";
	setAttr ".gem_dag_ctrls" -type "string" "pinky.L::ctrls.3";
	setAttr ".gem_dag_skin" -type "string" "pinky.L::hooks.last";
createNode joint -n "tpl_pinky_tip" -p "tpl_pinky_chain3";
	rename -uid "B0C4F82D-446D-93B0-4E74-FEBD7841E5AB";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	setAttr ".t" -type "double3" 0 0.16293054819107056 -0.021473867818713188 ;
	setAttr ".gem_hook" -type "string" "pinky.L::hooks.tip";
createNode transform -n "_shape_pinky_3_L" -p "tpl_pinky_chain3";
	rename -uid "BE08CB04-4E80-92F2-D2AC-62A119EB186F";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "pinky.L::ctrls.3";
createNode transform -n "shp_pinky_3_L" -p "_shape_pinky_3_L";
	rename -uid "BDA63AA5-49BC-D251-D946-F690BE568059";
	setAttr ".t" -type "double3" -5.5511151231257827e-17 0.012951500713825226 0.010736933909365476 ;
	setAttr ".s" -type "double3" 0.09766659140586853 0.082228310406208052 0.15016922354698181 ;
createNode nurbsCurve -n "cubeShape" -p "shp_pinky_3_L";
	rename -uid "7F068947-4DE2-6A22-D171-3B9EBEE54EBF";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 20;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.47209471 0.53715318 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "lightpink";
createNode pointConstraint -n "_shape_pinky_3_L_pointConstraint1" -p "_shape_pinky_3_L";
	rename -uid "53097B3E-4E91-8821-46E3-B89C62B0B038";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_pinky_chain3W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_pinky_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 5.5511151231257827e-17 0.08146527409553439 -0.010736933909356594 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_pinky_2_L" -p "tpl_pinky_chain2";
	rename -uid "6BEF3051-4552-CA86-3306-58B9773276E3";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "pinky.L::ctrls.2";
createNode transform -n "shp_pinky_2_L" -p "_shape_pinky_2_L";
	rename -uid "7D1F9B89-4638-8293-E9F4-45B213E6473C";
	setAttr ".t" -type "double3" -1.1102230246251565e-16 0.0086661428213199443 0.0157613400369776 ;
	setAttr ".s" -type "double3" 0.11009829491376877 0.10361309349536905 0.17751923203468334 ;
createNode nurbsCurve -n "cubeShape" -p "shp_pinky_2_L";
	rename -uid "2B3E3686-4940-F69D-186B-0C92A83069B8";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 21;
	setAttr ".ovrgb" -type "float3" 0.70933133 0.16223767 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "palevioletred";
createNode pointConstraint -n "_shape_pinky_2_L_pointConstraint1" -p "_shape_pinky_2_L";
	rename -uid "19FE6AB3-4299-9247-8AAD-4FAFBF8F4D67";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_pinky_chain2W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_pinky_chain3W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 2.2204460492503131e-16 0.097524970769881314 -0.015761340036986482 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_pinky_1_L" -p "tpl_pinky_chain1";
	rename -uid "5E5DFA72-4645-E841-6EEB-84B10B513852";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "pinky.L::ctrls.1";
createNode transform -n "shp_pinky_1_L" -p "_shape_pinky_1_L";
	rename -uid "26CDF4BE-4833-A4DF-616B-E7988A1EFF99";
	setAttr ".t" -type "double3" -1.1102230246251565e-16 0.030973494052891404 0.0078761000186169383 ;
	setAttr ".s" -type "double3" 0.082445204257965019 0.2295738160610199 0.24903316795825958 ;
createNode nurbsCurve -n "cubeShape" -p "shp_pinky_1_L";
	rename -uid "17C7FC01-45CE-56FE-5772-EBBA82D92B7D";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 9;
	setAttr ".ovrgb" -type "float3" 0.99142641 0.0036655408 0.29510069 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "deeppink";
createNode pointConstraint -n "_shape_pinky_1_L_pointConstraint1" -p "_shape_pinky_1_L";
	rename -uid "5AACDD17-47D4-56D9-674E-8DAD8D95E35E";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_pinky_chain1W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_pinky_chain2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 1.6653345369377348e-16 0.14122650027275085 -0.0078761000186187147 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_pinky_0_L" -p "tpl_pinky";
	rename -uid "05659C5F-4392-5FD6-89AF-8DB862A2158A";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "pinky.L::ctrls.0";
createNode transform -n "shp_pinky_0_L" -p "_shape_pinky_0_L";
	rename -uid "4AE8DF4D-4184-FA2D-D8AF-09B8113A9E3F";
	setAttr ".t" -type "double3" 0.032580419084947798 -0.23698371057913192 -0.0017166016971597031 ;
	setAttr ".r" -type "double3" -83.906945634181469 0.19981383127442018 3.1833631118872989 ;
	setAttr ".s" -type "double3" 0.10889182239770895 0.37233471870422358 0.1131555214524269 ;
createNode nurbsCurve -n "cubeShape" -p "shp_pinky_0_L";
	rename -uid "9BDB6D9E-48A8-AD90-47C8-4B9566D3BD8C";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 30;
	setAttr ".ovrgb" -type "float3" 0.32225022 0.027517317 0.60681796 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 0.66580650870882541
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		-0.66580650870882541 -0.50000000000000111 0.66580650870882541
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 0.6345999593201116
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		-0.63459334272345724 0.49999999999999811 -0.63459995932011204
		-0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.66580650870882541 -0.50000000000000111 -0.66580650870882541
		0.63459661913439602 0.49999999999999811 -0.63459995932011204
		;
	setAttr ".gem_color" -type "string" "darkorchid";
createNode pointConstraint -n "_shape_pinky_0_L_pointConstraint1" -p "_shape_pinky_0_L";
	rename -uid "F9F23D54-4FED-9A97-FF07-FE8CA100A1E9";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_pinkyW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_pinky_chain1W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.046455435454845317 0.2642426788806933 0.0047472137957793592 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode transform -n "_shape_arm_limb2_L" -p "tpl_arm_limb2";
	rename -uid "BA2B6701-4A04-F67D-5A97-248D6D58DE23";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.limb2";
createNode transform -n "shp_arm_limb2_L" -p "_shape_arm_limb2_L";
	rename -uid "716177AD-4BB7-0704-948C-A7AE49402A43";
	setAttr ".t" -type "double3" 1.0658141036401503e-14 3.5527136788005009e-15 3.3306690738754696e-16 ;
	setAttr ".s" -type "double3" 0.7897285255285319 0.78972852552852801 0.78972852552852635 ;
createNode nurbsCurve -n "circleShape" -p "shp_arm_limb2_L";
	rename -uid "F905C420-434E-5682-D00B-60A230E26386";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-0.7500001570034216 1.3307702705358707e-32 -1.9938877845559148e-16
		-0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		-2.2598967191885318e-16 -4.5924263801796575e-17 0.7500001570034216
		0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		0.7500001570034216 -2.4666010187879316e-32 4.2076903711413382e-16
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_limb2_L_pointConstraint1" -p "_shape_arm_limb2_L";
	rename -uid "827DB0A0-4340-6C59-BFEA-0F8F03F61053";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_limb2W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 3.5527136788005009e-15 8.8817841970012523e-16 -1.3877787807814457e-16 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_limb2_L_aimConstraint1" -p "_shape_arm_limb2_L";
	rename -uid "2092DBB1-456F-FA74-933F-DDB030A3F4B2";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 -1 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 179.02645650649004 3.0343528338837706 179.54427707124813 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_bend2_L" -p "tpl_arm_limb2";
	rename -uid "E866BBCF-4FA9-77E2-4D2E-7C994A694A02";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.bend2";
createNode transform -n "shp_arm_bend2_L" -p "_shape_arm_bend2_L";
	rename -uid "01547DA9-4DE3-BD87-0780-7ABE868D6457";
	setAttr ".t" -type "double3" -7.1054273576010019e-15 1.7763568394002505e-15 5.5511151231257827e-16 ;
	setAttr ".r" -type "double3" -2.0479882477369173 0 0 ;
	setAttr ".s" -type "double3" 0.58065736112692135 0.58065736112691524 0.58065736112691591 ;
createNode nurbsCurve -n "crossShape" -p "shp_arm_bend2_L";
	rename -uid "C018B887-4CB1-61CD-CBBC-44B8823718B4";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_bend2_L_pointConstraint1" -p "_shape_arm_bend2_L";
	rename -uid "C7BEE17F-46C2-AFE7-D537-CBA64981A3DF";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_limb2W0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_arm_limb3W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0.0094216550158385814 1.3355611350302947 0.022664159033135678 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_arm_bend2_L_aimConstraint1" -p "_shape_arm_bend2_L";
	rename -uid "390F16A2-43D6-97D9-65FA-67B9EB03062F";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 0.97217843299484086 0.0034286401579032731 -0.40412557272261729 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_tweak_L" -p "tpl_arm_limb2";
	rename -uid "E8F23808-466D-AF5E-38EC-2DB5FF08AD06";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.tweak";
createNode transform -n "shp_arm_tweak_L" -p "_shape_arm_tweak_L";
	rename -uid "787B1BF1-402A-5DF8-A45B-24A056BB4435";
	setAttr ".t" -type "double3" -1.7763568394002505e-15 2.6645352591003757e-15 3.8857805861880479e-16 ;
	setAttr ".r" -type "double3" -2.0479882477368707 0 0 ;
	setAttr ".s" -type "double3" 0.54175776885324445 0.54175776885323912 0.54175776885323779 ;
createNode nurbsCurve -n "crossShape" -p "shp_arm_tweak_L";
	rename -uid "FCB07C22-474E-AC0C-8375-E2A821129108";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_tweak_L_pointConstraint1" -p "_shape_arm_tweak_L";
	rename -uid "A2BDB621-4C5B-9AD6-5CB0-A4BB6853DAC0";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_limb2W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 3.5527136788005009e-15 8.8817841970012523e-16 -1.3877787807814457e-16 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_tweak_L_aimConstraint1" -p "_shape_arm_tweak_L";
	rename -uid "CD6D6033-4BB8-BD78-608A-73BBC23E9278";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 0.97217843299484119 0.0034286401579032653 -0.40412557272261618 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_arm_clav" -p "tpl_arm";
	rename -uid "816A9CA0-41C3-24A9-2929-99A95E75ADC5";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.65405917644073641 -0.95478767586762281 -0.015322695917946903 ;
	setAttr ".gem_template" -type "string" "clavicle";
	setAttr ".gem_hook" -type "string" "arm.L::hooks.clavicle";
	setAttr ".gem_dag_ctrls" -type "string" "arm.L::j.clavicle";
	setAttr ".gem_dag_skin" -type "string" "arm.L::hooks.clavicle";
createNode transform -n "_shape_arm_clavicle_L" -p "tpl_arm_clav";
	rename -uid "CED3CC7E-47E9-DF92-D1E8-C8981ED0572D";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.clavicle";
createNode transform -n "shp_arm_clavicle_L" -p "_shape_arm_clavicle_L";
	rename -uid "1640A6FF-4FBB-81C6-A64F-83BD9FE20A7A";
	setAttr ".t" -type "double3" 8.8817841970012523e-15 0.031794217744572251 -2.2204460492503131e-16 ;
	setAttr ".s" -type "double3" 1.534664931775944 1.0207924662591155 1.6398909052673141 ;
createNode nurbsCurve -n "circleShape" -p "shp_arm_clavicle_L";
	rename -uid "A58C6D0B-4CDF-5E4A-6242-EE9D4B76B119";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99609375 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-0.50000010466894773 8.8718018035724711e-33 -1.451255239964606e-16
		-0.35355343722788873 -2.1648905778322359e-17 0.35355343722788873
		-1.5065978127923546e-16 -3.0616175867864385e-17 0.50000010466894773
		0.35355343722788873 -2.1648905778322359e-17 0.35355343722788873
		0.50000010466894773 -1.6444006791919543e-32 2.6831301971668959e-16
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_arm_clavicle_L_pointConstraint1" -p "_shape_arm_clavicle_L";
	rename -uid "FFBE1C51-45DE-8575-0C9D-E5B8B87BCD75";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_arm_clavW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_armW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.32702958822036798 0.47739383793381229 0.0076613479589734412 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_arm_clavicle_L_aimConstraint1" -p "_shape_arm_clavicle_L";
	rename -uid "7578C62C-4288-E659-BD3E-AFB043ACA8B3";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_armW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 0.75854063398028004 -0.23487770307019792 34.409243374902537 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_limb1_L" -p "tpl_arm";
	rename -uid "D6BAAC55-49CA-BB92-9D3A-CD91B65A27D5";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.limb1";
createNode transform -n "shp_arm_limb1_L" -p "_shape_arm_limb1_L";
	rename -uid "BE2CD88D-4B37-22CA-74C2-B0A84794B962";
	setAttr ".t" -type "double3" -1.5987211554602254e-14 0.15705227841754166 -6.9388939039072284e-16 ;
	setAttr ".s" -type "double3" 1.0803870535966729 1.0803870535966733 0.69935344161260904 ;
createNode nurbsCurve -n "circleShape" -p "shp_arm_limb1_L";
	rename -uid "76C6B269-4F56-0E45-8A3F-338D8FFDC192";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-0.7500001570034216 1.3307702705358707e-32 -2.15088458422378e-16
		-0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		-2.2598967191885318e-16 -4.5924263801796575e-17 0.7500001570034216
		0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		0.7500001570034216 -2.4666010187879316e-32 4.0506935714734729e-16
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_limb1_L_pointConstraint1" -p "_shape_arm_limb1_L";
	rename -uid "BBAC985A-4D71-2E49-93C4-5C91985D823B";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_armW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 0 0 1.1102230246251565e-16 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_arm_limb1_L_aimConstraint1" -p "_shape_arm_limb1_L";
	rename -uid "B92DBEC1-4D6C-92BE-03C8-83A3FC4CAAF3";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb2W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 -1 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -179.13652769135385 2.9631061505900722 179.20290854744496 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_arm_bend1_L" -p "tpl_arm";
	rename -uid "E8855F7A-4AA3-CDCA-EBE5-8D8F3DA3A053";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "arm.L::ctrls.bend1";
createNode transform -n "shp_arm_bend1_L" -p "_shape_arm_bend1_L";
	rename -uid "3D549180-4520-20AE-09A6-DA864768BC2D";
	setAttr ".t" -type "double3" 1.7763568394002505e-15 1.7763568394002505e-15 0 ;
	setAttr ".r" -type "double3" 1.5919824158924574 0 0 ;
	setAttr ".s" -type "double3" 0.61840610514559846 0.61840610514559413 0.6184061051455958 ;
createNode nurbsCurve -n "crossShape" -p "shp_arm_bend1_L";
	rename -uid "F3D5E48F-4972-4944-1FC4-A89BBC0A826C";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_arm_bend1_L_pointConstraint1" -p "_shape_arm_bend1_L";
	rename -uid "B5CEF5BB-477E-E872-4318-5B83F05C8690";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_armW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_arm_limb2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0.019903670030958054 1.3547265167418487 -0.020392759686078898 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_arm_bend1_L_aimConstraint1" -p "_shape_arm_bend1_L";
	rename -uid "2EF81F99-4846-B72D-0D34-6198CEBB7A9F";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_arm_limb2W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -0.86231778825091487 -0.0063336557295869539 -0.84163488774618411 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_neck" -p "tpl_spine_tip";
	rename -uid "9FB38D53-4BD4-80EB-C9F9-08AA172062DC";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 0.7566105831217218 -0.1816629073973432 ;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "neck";
	setAttr ".gem_module" -type "string" "neck.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy neck from ttRig3\n\nstructure:\n  root: .\n  chain: /*\n  tip: /-1\n  head: /-2\n\nnames:\n  head: head\n\nopts:\n  merge:\n    value: 1\n  flip:\n    value: x\n\n  bones:\n    value: 2\n  bones_length:\n    value: 0\n    enum:\n     0: equal\n     1: parametric\n\n  orient_neck:\n    value: on\n  aim_axis:\n    value: y\n  up_axis:\n    value: x\n\n  default_stretch:\n    value: on";
	setAttr ".ui_expanded" no;
	setAttr ".gem_hook" -type "string" "neck::hooks.neck.0";
	setAttr ".gem_dag_ctrls" -type "string" "neck::ctrls.fk.0";
	setAttr ".gem_dag_skin" -type "string" "neck::skin.neck0";
createNode joint -n "tpl_neck_head" -p "tpl_neck";
	rename -uid "378FAC0F-4DC4-A63F-19E9-7EB3B91FE0EF";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 1.4465575352570248 0.19459461136701223 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_hook" -type "string" "neck::hooks.head";
	setAttr ".gem_dag_ctrls" -type "string" "neck::ctrls.head";
	setAttr ".gem_dag_skin" -type "string" "neck::skin.head";
createNode joint -n "tpl_neck_tip" -p "tpl_neck_head";
	rename -uid "BFAAD3D5-4760-511B-735B-15B75B612972";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 2.1620022614676078 0 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_hook" -type "string" "neck::hooks.head";
	setAttr ".gem_dag_ctrls" -type "string" "neck::ctrls.fk.0";
	setAttr ".gem_dag_skin" -type "string" "neck::skin.neck1";
createNode transform -n "_shape_neck_head" -p "tpl_neck_head";
	rename -uid "2776A936-46F2-B97A-AD5D-4AB056011AAF";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "neck::ctrls.head";
createNode transform -n "shp_neck_head" -p "_shape_neck_head";
	rename -uid "233DE36E-46D8-21A5-75FD-97AC4AB8A160";
	setAttr ".t" -type "double3" 0 2.7755575615628914e-17 -0.13394890211477772 ;
	setAttr ".s" -type "double3" 0.40392061625268399 0.52691770884715772 0.52691770884715772 ;
createNode nurbsCurve -n "circleShape" -p "shp_neck_head";
	rename -uid "9E90F43F-45D4-BA71-6E22-F2B733513E9B";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 17;
	setAttr ".ovrgb" -type "float3" 0.99609375 0.99609375 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		2.7474576015341636 1.6823326966330744e-16 -2.7474576015341636
		-4.4328818990031942e-16 2.3791776931262594e-16 -3.8854921030087959
		-2.7474576015341636 1.6823326966330744e-16 -2.7474576015341636
		-3.8854921030087968 6.8942617262177645e-32 -1.1323624965780092e-15
		-2.7474576015341636 -1.6823326966330744e-16 2.7474576015341636
		-1.1707745357155265e-15 -2.3791776931262594e-16 3.8854921030087959
		2.7474576015341636 -1.6823326966330744e-16 2.7474576015341636
		3.8854921030087968 -1.2778609031318155e-31 2.1029589222163031e-15
		2.7474576015341636 1.6823326966330744e-16 -2.7474576015341636
		-4.4328818990031942e-16 2.3791776931262594e-16 -3.8854921030087959
		-2.7474576015341636 1.6823326966330744e-16 -2.7474576015341636
		;
	setAttr ".gem_color" -type "string" "yellow";
createNode pointConstraint -n "_shape_neck_head_pointConstraint1" -p "_shape_neck_head";
	rename -uid "C35544D9-41D8-2AD9-92F3-718864B19586";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_neck_headW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_neck_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 1.081001130733803 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_neck_head_aimConstraint1" -p "_shape_neck_head";
	rename -uid "1E2E836F-4012-85F3-3EC9-88A26A30A980";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_neck_tipW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 1 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" -90 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_neck_scale" -p "tpl_neck_head";
	rename -uid "2CD0E0E4-46AA-9D7E-67C4-0680E26FED57";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "neck::ctrls.scale";
createNode transform -n "shp_neck_scale" -p "_shape_neck_scale";
	rename -uid "5628F214-4E4B-31BB-29B3-B994A910A32C";
	setAttr ".s" -type "double3" 1.170501815889716 1.170501815889716 1.170501815889716 ;
createNode nurbsCurve -n "scaleShape" -p "shp_neck_scale";
	rename -uid "682F2E9E-4237-ACE1-F5E6-6596CF9E73BA";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35355343722788873 0.35355343722788873 -5.6855731989364301e-17
		-5.7044033412661999e-17 0.50000010466894773 -8.0406146850137582e-17
		-0.35355343722788873 0.35355343722788873 -5.6855731989364301e-17
		-0.50000010466894773 1.4488751323080309e-16 -2.3299690156243639e-32
		-0.35355343722788873 -0.35355343722788873 5.6855731989364301e-17
		-1.5065978127923546e-16 -0.50000010466894773 8.0406146850137582e-17
		0.35355343722788873 -0.35355343722788873 5.6855731989364301e-17
		0.50000010466894773 -2.6855103048234708e-16 4.3186296696006676e-32
		0.35355343722788873 0.35355343722788873 -5.6855731989364301e-17
		-5.7044033412661999e-17 0.50000010466894773 -8.0406146850137582e-17
		-0.35355343722788873 0.35355343722788873 -5.6855731989364301e-17
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape4" -p "shp_neck_scale";
	rename -uid "2B072A75-4CE4-77A2-44C3-D897BF53F375";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		1.760341235909876e-17 0.35355343722788873 -0.35355343722788873
		-8.6127335734020952e-17 -2.7908867287728827e-16 -0.50000010466894773
		-1.3940586019058573e-16 -0.35355343722788873 -0.35355343722788873
		-1.110223257036908e-16 -0.50000010466894773 2.1645966367666613e-17
		-1.760341235909876e-17 -0.35355343722788873 0.35355343722788873
		8.6127335734020952e-17 7.1384858185390792e-17 0.50000010466894773
		1.3940586019058573e-16 0.35355343722788873 0.35355343722788873
		1.110223257036908e-16 0.50000010466894773 1.0201753595543325e-16
		1.760341235909876e-17 0.35355343722788873 -0.35355343722788873
		-8.6127335734020952e-17 -2.7908867287728827e-16 -0.50000010466894773
		-1.3940586019058573e-16 -0.35355343722788873 -0.35355343722788873
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape5" -p "shp_neck_scale";
	rename -uid "7AC5B297-41AF-7D65-FE2D-5D9002EC0B2B";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-0.50000010466894773 8.8718018035724711e-33 -1.4488751323080309e-16
		-0.35355343722788873 -2.1648905778322359e-17 0.35355343722788873
		-1.5065978127923546e-16 -3.0616175867864385e-17 0.50000010466894773
		0.35355343722788873 -2.1648905778322359e-17 0.35355343722788873
		0.50000010466894773 -1.6444006791919543e-32 2.6855103048234708e-16
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788873
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape6" -p "shp_neck_scale";
	rename -uid "DC4BBFFB-432B-4EF7-C70D-67A62B7E8DD9";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 7 0 no 3
		8 0 1 2 3 4 5 6 7
		8
		0 -0.45118453989102997 0
		0 0.45118453989102997 0
		0 0 0
		0 0 0.45118453989102997
		0 0 -0.45118453989102997
		0 0 0
		-0.45118453989102997 0 0
		0.45118453989102997 0 0
		;
	setAttr -k on ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_neck_scale_pointConstraint1" -p "_shape_neck_scale";
	rename -uid "91C4C6D0-4DD0-60D7-6F33-32B825D4809A";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_neck_headW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_neck_mid" -p "tpl_neck";
	rename -uid "D6C0A39C-401C-D552-946F-76A48948D130";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "neck::ctrls.mid";
createNode transform -n "shp_neck_mid" -p "_shape_neck_mid";
	rename -uid "1FD773B9-4917-5F8C-0A88-6D8D3576159B";
	setAttr ".s" -type "double3" 0.78987341043339199 0.78987341043339077 0.78987341043339077 ;
createNode nurbsCurve -n "crossShape" -p "shp_neck_mid";
	rename -uid "A4FD48F6-4D48-0326-79C4-66A6D1CA8114";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_neck_mid_pointConstraint1" -p "_shape_neck_mid";
	rename -uid "C4118DD2-4FB4-123B-8AA6-6A8C51BB51D4";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_neckW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_neck_headW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 0.7232787676285124 0.097297305683506113 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_neck_mid_aimConstraint1" -p "_shape_neck_mid";
	rename -uid "A0502DAB-42C4-7209-9A26-47AFBDBC53EE";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_neck_headW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 7.6615799550524706 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_neck_neck0" -p "tpl_neck";
	rename -uid "10A4BDEE-4B40-08F0-F562-DDACFEEBCBB9";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "neck::ctrls.neck0";
createNode transform -n "shp_neck_neck0" -p "_shape_neck_neck0";
	rename -uid "742FC700-4C7F-819F-366D-2B848CC26E37";
	setAttr ".t" -type "double3" 0 0.205101201788775 0 ;
	setAttr ".s" -type "double3" 0.85439810762755486 0.85439810762755486 0.85439810762755486 ;
createNode nurbsCurve -n "circleShape" -p "shp_neck_neck0";
	rename -uid "E5307388-4F2C-B5A4-1358-ECAD6043CFA6";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 22;
	setAttr ".ovrgb" -type "float3" 0.9375 0.8984375 0.546875 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.70710687445577747 4.3297811556644719e-17 -0.70710687445577747
		-1.14088066825324e-16 6.1232351735728771e-17 -1.0000002093378955
		-0.70710687445577747 4.3297811556644719e-17 -0.70710687445577747
		-1.0000002093378955 1.7743603607144942e-32 -2.8977502646160617e-16
		-0.70710687445577747 -4.3297811556644719e-17 0.70710687445577747
		-3.0131956255847093e-16 -6.1232351735728771e-17 1.0000002093378955
		0.70710687445577747 -4.3297811556644719e-17 0.70710687445577747
		1.0000002093378955 -3.2888013583839086e-32 5.3710206096469417e-16
		0.70710687445577747 4.3297811556644719e-17 -0.70710687445577747
		-1.14088066825324e-16 6.1232351735728771e-17 -1.0000002093378955
		-0.70710687445577747 4.3297811556644719e-17 -0.70710687445577747
		;
	setAttr ".gem_color" -type "string" "khaki";
createNode pointConstraint -n "_shape_neck_neck0_pointConstraint1" -p "_shape_neck_neck0";
	rename -uid "74265E5F-4769-2407-B507-F08A64112F93";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_neckW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_neck_neck0_aimConstraint1" -p "_shape_neck_neck0";
	rename -uid "70C72FB9-4E8C-5B35-D548-B09B919E7775";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_neck_headW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 7.6615799550525168 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_neck_ctrls_head_offset" -p "tpl_neck";
	rename -uid "E23DFD5E-4138-803B-02AC-99A32DA545BA";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "neck::ctrls.head_offset";
createNode pointConstraint -n "_shape_neck_ctrls_head_offset_pointConstraint1" -p
		 "_shape_neck_ctrls_head_offset";
	rename -uid "3E6643C5-4257-3B60-EE31-3181BA10A5E3";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_neck_headW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_neck_tipW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 2.5275586659908296 0.19459461136701223 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_neck_ctrls_head_offset_aimConstraint1" -p "_shape_neck_ctrls_head_offset";
	rename -uid "86C6176D-428C-1DAF-84ED-088CF2B54537";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_neck_tipW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 1 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" -90 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_spineIK" -p "tpl_spine_tip";
	rename -uid "5E875040-4430-624B-C9A6-05AFA99C1AE8";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.spineIK";
createNode transform -n "shp_spine_spineIK" -p "_shape_spine_spineIK";
	rename -uid "BC8DD83B-4337-5729-75F1-FD9FF6FAC929";
	setAttr ".s" -type "double3" 1.1049549139447208 1.1049549139447208 1.1049549139447208 ;
createNode nurbsCurve -n "rhombusShape" -p "shp_spine_spineIK";
	rename -uid "0C92C3DA-4095-D01F-98AA-B1A0F5E333EA";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 17;
	setAttr ".ovrgb" -type "float3" 0.99609375 0.99609375 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 4 0 no 3
		5 0 1 2 3 4
		5
		1.75 0 0
		0 0 -1.75
		-1.75 0 0
		0 0 1.75
		1.75 0 0
		;
	setAttr ".gem_color" -type "string" "yellow";
createNode pointConstraint -n "_shape_spine_spineIK_pointConstraint1" -p "_shape_spine_spineIK";
	rename -uid "A70CA30E-4A12-B96F-56D4-AFB3ABC256F4";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spine_tipW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "aimConstraint106" -p "_shape_spine_spineIK";
	rename -uid "7311A081-413C-CC37-615D-77B3A880A34E";
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".hio" yes;
createNode pointConstraint -n "pointConstraint106" -p "_shape_spine_spineIK";
	rename -uid "565DF5BF-421C-9267-A682-4F8506CFB93A";
	setAttr ".o" -type "double3" 0 1 0 ;
	setAttr ".hio" yes;
createNode transform -n "_shape_spine_spine2" -p "tpl_spine_chain2";
	rename -uid "E22CE9FD-4047-EE1F-A938-2BBF9A6069FF";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.spine2";
createNode transform -n "shp_spine_spine2" -p "_shape_spine_spine2";
	rename -uid "FADA462A-4617-1C12-8410-038B4F128789";
	setAttr ".s" -type "double3" 1.0886551443770387 1.0886551443770387 1.0886551443770387 ;
createNode nurbsCurve -n "circleShape" -p "shp_spine_spine2";
	rename -uid "BF6C7672-431B-F142-7F83-4EB5E0D1B0E3";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 22;
	setAttr ".ovrgb" -type "float3" 0.9375 0.8984375 0.546875 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.7113210023798602e-16 9.184852760359315e-17 -1.5000003140068432
		-1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.5000003140068432 2.6615405410717413e-32 -4.3466253969240926e-16
		-1.0606603116836661 -6.4946717334967081e-17 1.0606603116836661
		-4.5197934383770636e-16 -9.184852760359315e-17 1.5000003140068432
		1.0606603116836661 -6.4946717334967081e-17 1.0606603116836661
		1.5000003140068432 -4.9332020375758631e-32 8.056530914470413e-16
		1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.7113210023798602e-16 9.184852760359315e-17 -1.5000003140068432
		-1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		;
	setAttr ".gem_color" -type "string" "khaki";
createNode pointConstraint -n "_shape_spine_spine2_pointConstraint1" -p "_shape_spine_spine2";
	rename -uid "AFEBEBA6-49CE-D33A-649D-738C36676EB9";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spine_chain2W0" -dv 1 -min 0 
		-at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_spine1" -p "tpl_spine_chain1";
	rename -uid "A2EE27AE-4D8A-B9FD-F9CB-8DB86263D9E6";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.spine1";
createNode transform -n "shp_spine_spine1" -p "_shape_spine_spine1";
	rename -uid "B133EC3A-40A0-D4D1-95D1-1CA403F7E0E5";
	setAttr ".s" -type "double3" 1.0892680684344409 1.0892680684344409 1.0892680684344409 ;
createNode nurbsCurve -n "circleShape" -p "shp_spine_spine1";
	rename -uid "A85C05CF-41CF-C274-AC40-448BF5E616E2";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 22;
	setAttr ".ovrgb" -type "float3" 0.9375 0.8984375 0.546875 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.7113210023798602e-16 9.184852760359315e-17 -1.5000003140068432
		-1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.5000003140068432 2.6615405410717413e-32 -4.3466253969240926e-16
		-1.0606603116836661 -6.4946717334967081e-17 1.0606603116836661
		-4.5197934383770636e-16 -9.184852760359315e-17 1.5000003140068432
		1.0606603116836661 -6.4946717334967081e-17 1.0606603116836661
		1.5000003140068432 -4.9332020375758631e-32 8.056530914470413e-16
		1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		-1.7113210023798602e-16 9.184852760359315e-17 -1.5000003140068432
		-1.0606603116836661 6.4946717334967081e-17 -1.0606603116836661
		;
	setAttr ".gem_color" -type "string" "khaki";
createNode pointConstraint -n "_shape_spine_spine1_pointConstraint1" -p "_shape_spine_spine1";
	rename -uid "7D404277-454C-E0B9-4CBD-DF8BB321C997";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spine_chain1W0" -dv 1 -min 0 
		-at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_spine_mid" -p "tpl_spine_chain1";
	rename -uid "885AB570-47C9-F00F-F7BC-A39F0069779E";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.spine_mid";
createNode transform -n "shp_spine_spine_mid" -p "_shape_spine_spine_mid";
	rename -uid "EE4675EE-4B67-FDFD-C245-63A4FF6FF07F";
	setAttr ".r" -type "double3" 0 180 0 ;
	setAttr ".s" -type "double3" 0.79775691437615881 0.66519340673367355 0.66519340673367378 ;
createNode nurbsCurve -n "crossShape" -p "shp_spine_spine_mid";
	rename -uid "43A63B49-47AB-9A6F-EF3B-FC974E4C5451";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1.75 0 0
		0 0 0
		0 0 1.75
		0 0 0
		-1.75 0 0
		0 0 0
		0 0 -1.75
		;
	setAttr ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_spine_spine_mid_pointConstraint1" -p "_shape_spine_spine_mid";
	rename -uid "168093FC-4C75-6216-3171-4384C1C74090";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spine_chain1W0" -dv 1 -min 0 
		-at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_spine_chain2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0 0.4647301280723557 0.01286682349929319 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_spine_spine_mid_aimConstraint1" -p "_shape_spine_spine_mid";
	rename -uid "1DF2C9FA-44C1-1EFE-48AB-77AEEA5C33B8";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_spine_chain2W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 1.5859234283410295 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_spine_hips" -p "tpl_spine";
	rename -uid "5C542B86-4E8F-BAFA-A37A-35ACC2E6CDFA";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 -0.73857300055242625 -0.029358634517053478 ;
	setAttr ".mnrl" -type "double3" -360 -360 -360 ;
	setAttr ".mxrl" -type "double3" 360 360 360 ;
	setAttr ".gem_template" -type "string" "hips";
	setAttr ".gem_hook" -type "string" "spine::hooks.pelvis";
	setAttr ".gem_dag_ctrls" -type "string" "spine::ctrls.pelvisIK";
	setAttr ".gem_dag_skin" -type "string" "spine::skin.pelvis";
createNode joint -n "tpl_leg" -p "tpl_spine_hips";
	rename -uid "9D5B15A0-4F74-1AE4-CA75-548B1D7D6754";
	addAttr -ci true -sn "gem_type" -ln "gem_type" -dt "string";
	addAttr -ci true -sn "gem_id" -ln "gem_id" -dt "string";
	addAttr -ci true -sn "gem_module" -ln "gem_module" -dt "string";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	addAttr -ci true -sn "gem_opt_forks" -ln "gem_opt_forks" -dt "string";
	addAttr -ci true -sn "nts" -ln "notes" -dt "string";
	addAttr -ci true -sn "gem_var_shear_up_base_0" -ln "gem_var_shear_up_base_0" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_base_1" -ln "gem_var_shear_up_base_1" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_tip_2" -ln "gem_var_shear_up_tip_2" -at "double";
	addAttr -ci true -sn "gem_var_shear_up_tip_3" -ln "gem_var_shear_up_tip_3" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_base_0" -ln "gem_var_shear_dn_base_0" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_base_1" -ln "gem_var_shear_dn_base_1" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_tip_2" -ln "gem_var_shear_dn_tip_2" -at "double";
	addAttr -ci true -sn "gem_var_shear_dn_tip_3" -ln "gem_var_shear_dn_tip_3" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_0" -ln "gem_var_tw_dn_0" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_1" -ln "gem_var_tw_dn_1" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_2" -ln "gem_var_tw_dn_2" -at "double";
	addAttr -ci true -sn "gem_var_tw_dn_3" -ln "gem_var_tw_dn_3" -at "double";
	addAttr -ci true -sn "ui_expanded" -ln "ui_expanded" -dv 1 -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.67113356777712063 5.7189291904790545e-05 6.5267390381151813e-09 ;
	setAttr ".r" -type "double3" 0 0 0.5 ;
	setAttr ".jo" -type "double3" 0 0 180 ;
	setAttr ".uocol" yes;
	setAttr ".oclr" -type "float3" 0.33000001 0.73000002 1 ;
	setAttr -l on ".gem_type" -type "string" "template";
	setAttr ".gem_id" -type "string" "leg";
	setAttr ".gem_module" -type "string" "leg.legacy";
	setAttr ".gem_template" -type "string" "[template]\ndesc: legacy leg from ttRig3\n\nstructure:\n  clavicle:\n  limb1: .\n  limb2: /1\n  limb3: /2\n  digits: /3\n  tip: /4\n  heel:\n\nnames:\n  limb: leg\n  clavicle: pelvis\n  limb1: hip\n  limb2: knee\n  limb3: ankle\n  digits: toes\n  effector: foot\n  heel: heel\n\nopts:\n  forks:\n    value: \"['L', 'R']\"\n    literal: on\n  merge:\n    value: 1\n    \n  aim_axis:\n    value: y\n  up_axis:\n    value: -x\n  up_axis2:\n    value: z\n    \n  reverse_lock:\n    value: on\n  clavicle:\n    value: off\n  pv_space:\n    value: space.cog\n\n  default_stretch:\n    value: on\n  soft_distance:\n    value: 0.05\n    min: 0\n    max: 1\n\n  blend_joints:\n    value: on\n\n  twist_joints_up:\n    value: 3\n    min: 2\n  twist_joints_dn:\n    value: 3\n    min: 2\n  deform_chains:\n    value: 1\n    min: 1\n    max: 5";
	setAttr ".gem_opt_forks" -type "string" "[L, R]";
	setAttr ".nts" -type "string" "[mod]\n# -- leg settings\n\nplug:\n node: leg.L::weights.0\n\n twist_dn_0: $tw_dn_0\n twist_dn_1: $tw_dn_1\n twist_dn_2: $tw_dn_2\n twist_dn_3: $tw_dn_3\n\n shear_up_base_0: $shear_up_base_0\n shear_up_base_1: $shear_up_base_1\n shear_up_tip_2:  $shear_up_tip_2\n shear_up_tip_3:  $shear_up_tip_3\n shear_dn_base_0: $shear_dn_base_0\n shear_dn_base_1: $shear_dn_base_1\n shear_dn_tip_2:  $shear_dn_tip_2\n shear_dn_tip_3:  $shear_dn_tip_3\n";
	setAttr -k on ".gem_var_shear_up_base_0" 0.75;
	setAttr -k on ".gem_var_shear_up_base_1";
	setAttr -k on ".gem_var_shear_up_tip_2";
	setAttr -k on ".gem_var_shear_up_tip_3" 0.75;
	setAttr -k on ".gem_var_shear_dn_base_0" 0.75;
	setAttr -k on ".gem_var_shear_dn_base_1";
	setAttr -k on ".gem_var_shear_dn_tip_2";
	setAttr -k on ".gem_var_shear_dn_tip_3" 0.5;
	setAttr -k on ".gem_var_tw_dn_0" 0.15;
	setAttr -k on ".gem_var_tw_dn_1" 0.4;
	setAttr -k on ".gem_var_tw_dn_2" 0.6;
	setAttr -k on ".gem_var_tw_dn_3" 0.85;
	setAttr ".gem_hook" -type "string" "leg.L::hooks.limb1";
	setAttr ".gem_dag_ctrls" -type "string" "leg.L::ctrls.limb1";
	setAttr ".gem_dag_skin" -type "string" "leg.L::skin.up.0";
createNode joint -n "tpl_leg_limb2" -p "tpl_leg";
	rename -uid "90720F89-4D1F-3623-130C-38AA3BF4AF25";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.044534191137000079 4.813423789300793 0.062450385617214582 ;
	setAttr ".gem_hook" -type "string" "leg.L::hooks.limb2";
	setAttr ".gem_dag_ctrls" -type "string" "leg.L::ctrls.limb2";
	setAttr ".gem_dag_skin" -type "string" "leg.L::skin.dn.0";
createNode joint -n "tpl_leg_limb3" -p "tpl_leg_limb2";
	rename -uid "BBE99BFA-49D1-877D-A7A5-3CA97506EEF3";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_ctrls" -ln "gem_dag_ctrls" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0.044622895013786239 4.8212453348749342 -0.20621729174597797 ;
	setAttr ".r" -type "double3" 0 -0.5 0 ;
	setAttr ".jo" -type "double3" 89.999999999999986 0 0 ;
	setAttr ".gem_hook" -type "string" "leg.L::hooks.effector";
	setAttr ".gem_dag_ctrls" -type "string" "leg.L::ctrls.limb3";
	setAttr ".gem_dag_skin" -type "string" "leg.L::hooks.effector";
createNode joint -n "tpl_leg_digits" -p "tpl_leg_limb3";
	rename -uid "1F06DBD9-483A-48E1-0E13-4CB9E654C850";
	addAttr -ci true -sn "gem_hook" -ln "gem_hook" -dt "string";
	addAttr -ci true -sn "gem_dag_skin" -ln "gem_dag_skin" -dt "string";
	setAttr ".t" -type "double3" 0 1.20008802963283 -0.59439390952084881 ;
	setAttr ".gem_hook" -type "string" "leg.L::hooks.digits";
	setAttr ".gem_dag_skin" -type "string" "leg.L::hooks.digits";
createNode joint -n "tpl_leg_tip" -p "tpl_leg_digits";
	rename -uid "6DBC612C-406C-844C-524F-07A17B821DB9";
	setAttr ".t" -type "double3" 0 0.98272529139872211 -0.19660975559400612 ;
createNode transform -n "_shape_leg_digits_L" -p "tpl_leg_digits";
	rename -uid "E5950923-4717-3664-43BC-619001BAC254";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.digits";
createNode transform -n "shp_leg_digits_L" -p "_shape_leg_digits_L";
	rename -uid "46081D14-4631-557C-F58E-26A3F720C9E5";
	setAttr ".t" -type "double3" 4.4408920985006262e-16 1.3322676295501878e-15 5.5511151231257827e-17 ;
	setAttr ".s" -type "double3" 1.409295293911013 1.381872253390579 0.8620137188519279 ;
createNode nurbsCurve -n "circleShape" -p "shp_leg_digits_L";
	rename -uid "33845490-4C47-FC97-20F9-C58B8F719EB9";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99609375 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788879
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788879
		-0.50000010466894773 8.8718018035724711e-33 -1.7535289123496446e-16
		-0.35355343722788873 -2.1648905778322359e-17 0.35355343722788868
		-1.5065978127923546e-16 -3.0616175867864385e-17 0.50000010466894773
		0.35355343722788873 -2.1648905778322359e-17 0.35355343722788868
		0.50000010466894773 -1.6444006791919543e-32 2.3808565247818571e-16
		0.35355343722788873 2.1648905778322359e-17 -0.35355343722788879
		-5.7044033412661999e-17 3.0616175867864385e-17 -0.50000010466894773
		-0.35355343722788873 2.1648905778322359e-17 -0.35355343722788879
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_leg_digits_L_pointConstraint1" -p "_shape_leg_digits_L";
	rename -uid "D64028CE-4EF9-9F64-BC08-3BB2E87C9938";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_digitsW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_leg_digits_L_aimConstraint1" -p "_shape_leg_digits_L";
	rename -uid "82796CBC-4EB8-EC31-EBCE-CC9860A43F55";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_tipW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -11.313559393495021 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_leg_bank_ext" -p "tpl_leg_digits";
	rename -uid "6F8F0434-4797-0EA4-05D2-7190A974C6CD";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	setAttr ".t" -type "double3" -0.60976690786802501 0.052895130244078187 -0.19588377773941684 ;
	setAttr ".jo" -type "double3" 0 0 5.5173828725626996e-33 ;
	setAttr ".gem_template" -type "string" "bank_ext";
createNode joint -n "tpl_leg_bank_int" -p "tpl_leg_digits";
	rename -uid "96FD067E-4D32-6850-651B-2ABDD4FD8C5F";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	setAttr ".t" -type "double3" 0.59269553462879432 0.052895130244078187 -0.19588377773941684 ;
	setAttr ".gem_template" -type "string" "bank_int";
createNode transform -n "_shape_leg_ctrls_ik_offset_L" -p "tpl_leg_digits";
	rename -uid "5F5DCB8B-49F9-6AE3-89D3-D48DBECD02CA";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.ik_offset";
createNode pointConstraint -n "_shape_leg_ctrls_ik_offset_L_pointConstraint1" -p "_shape_leg_ctrls_ik_offset_L";
	rename -uid "13F14E0F-459D-FA99-5E75-D1A3AD0094B2";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_digitsW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_leg_ctrls_ik_offset_L_aimConstraint1" -p "_shape_leg_ctrls_ik_offset_L";
	rename -uid "B509B650-41F5-9157-D657-02B3D5D6C39D";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 1 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" 63.651157262880687 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_leg_heel" -p "tpl_leg_limb3";
	rename -uid "5DC713DA-4EA1-C709-BD35-AD94D9BEAE90";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	setAttr ".t" -type "double3" 8.890664558743268e-20 -0.21439847296506803 -0.79027768726026537 ;
	setAttr ".gem_template" -type "string" "heel";
createNode transform -n "_shape_leg_limb3_L" -p "tpl_leg_limb3";
	rename -uid "DF728B27-47DC-D5A7-32E4-4EAC8F2F1411";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.limb3";
createNode transform -n "shp_leg_limb3_L" -p "_shape_leg_limb3_L";
	rename -uid "9B1274CA-40BF-C902-CE45-148C387F31F1";
	setAttr ".t" -type "double3" 1.1102230246251565e-16 0.10323270929732042 0.098903170009978059 ;
	setAttr ".s" -type "double3" 0.63082486633412116 0.63082486633412116 0.6308248663341236 ;
createNode nurbsCurve -n "circleShape" -p "shp_leg_limb3_L";
	rename -uid "0C5C647C-4A0E-1D05-41DC-4E927F7E20B0";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183318 3.2473358667483541e-17 -0.53033015584183307
		5.7973881005912261e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183296 3.2473358667483541e-17 -0.53033015584183307
		-0.75000015700342149 1.3307702705358707e-32 -2.3527376123681778e-16
		-0.53033015584183296 -3.2473358667483541e-17 0.53033015584183307
		-8.2449740793947898e-17 -4.5924263801796575e-17 0.7500001570034216
		0.53033015584183318 -3.2473358667483541e-17 0.53033015584183307
		0.75000015700342171 -2.4666010187879316e-32 3.8488405433290748e-16
		0.53033015584183318 3.2473358667483541e-17 -0.53033015584183307
		5.7973881005912261e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183296 3.2473358667483541e-17 -0.53033015584183307
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_limb3_L_pointConstraint1" -p "_shape_leg_limb3_L";
	rename -uid "0D61D1A2-4774-740E-0841-20A28A5746B5";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 6.9388939039072284e-18 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "aimConstraint107" -p "_shape_leg_limb3_L";
	rename -uid "5A3D4D2C-48F2-6931-F0C3-04A957C72EF9";
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 1 ;
	setAttr ".wut" 1;
	setAttr ".hio" yes;
createNode pointConstraint -n "pointConstraint107" -p "_shape_leg_limb3_L";
	rename -uid "8364B674-4288-DAD4-DAC9-F2AF4ECC44FA";
	setAttr ".o" -type "double3" 0 1 0 ;
	setAttr ".hio" yes;
createNode transform -n "_shape_leg_ik_L" -p "tpl_leg_limb3";
	rename -uid "CD628F1A-4943-9FDE-D070-3FB5EE68D10B";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.ik";
createNode transform -n "shp_leg_ik_L" -p "_shape_leg_ik_L";
	rename -uid "71188E45-42B9-4097-729F-1C90E2223439";
	setAttr ".t" -type "double3" 0.1353880428442874 -0.70945921935484424 1.0060946869767697 ;
	setAttr ".s" -type "double3" 0.9666512063362046 0.72929799642242021 2.0476874715881892 ;
createNode nurbsCurve -n "squareShape" -p "shp_leg_ik_L";
	rename -uid "12BFFB7D-49FF-12BA-50FA-6C80A3EC8283";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99609375 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 4 0 no 3
		5 0 1 2 3 4
		5
		0.75000000000000011 0 0.75
		0.75000000000000011 0 -0.75
		-0.74999999999999989 0 -0.75
		-0.74999999999999989 0 0.75
		0.75000000000000011 0 0.75
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_leg_ik_L_pointConstraint1" -p "_shape_leg_ik_L";
	rename -uid "2491CDFE-48C3-13AD-94DF-7788AC3F580E";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 6.9388939039072284e-18 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "aimConstraint108" -p "_shape_leg_ik_L";
	rename -uid "1582D402-45CC-069F-0ABF-099681A345DD";
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 1 ;
	setAttr ".wut" 1;
	setAttr ".hio" yes;
createNode pointConstraint -n "pointConstraint108" -p "_shape_leg_ik_L";
	rename -uid "3D818A1A-4AD6-B601-9123-90956C7F37EA";
	setAttr ".o" -type "double3" 0 1 0 ;
	setAttr ".hio" yes;
createNode transform -n "_shape_leg_limb2_L" -p "tpl_leg_limb2";
	rename -uid "4622DFDC-43B0-BE2D-9A05-2396FEBFA934";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.limb2";
createNode transform -n "shp_leg_limb2_L" -p "_shape_leg_limb2_L";
	rename -uid "7399C30B-4AAD-D00B-0D5E-608054B4D301";
	setAttr ".t" -type "double3" 5.5511151231257827e-16 0 1.3877787807814457e-16 ;
	setAttr ".s" -type "double3" 1.0171518567488502 1.017151856748862 1.0171518567488493 ;
createNode nurbsCurve -n "circleShape" -p "shp_leg_limb2_L";
	rename -uid "C06340C1-43CC-9512-79F6-1A93AC7287A7";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-0.7500001570034216 1.3307702705358707e-32 -2.1733126984620463e-16
		-0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		-2.2598967191885318e-16 -4.5924263801796575e-17 0.7500001570034216
		0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		0.7500001570034216 -2.4666010187879316e-32 4.0282654572352065e-16
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_limb2_L_pointConstraint1" -p "_shape_leg_limb2_L";
	rename -uid "BBF0C59B-416A-6027-FF75-549B31727414";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_limb2W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_leg_limb2_L_aimConstraint1" -p "_shape_leg_limb2_L";
	rename -uid "8483C40C-4435-A147-04FD-EC90B57FE3C8";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 -1 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -2.4490929770573997 -0.011324883343392649 -0.52979989357640012 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_leg_bend2_L" -p "tpl_leg_limb2";
	rename -uid "B58E8F6D-45D5-4949-C7EE-B7BF900675DD";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.bend2";
createNode transform -n "shp_leg_bend2_L" -p "_shape_leg_bend2_L";
	rename -uid "9A1A6A9B-4BA2-19E2-3D24-49AD170460A3";
	setAttr ".t" -type "double3" -5.5511151231257827e-16 -2.2204460492503131e-15 2.7755575615628914e-17 ;
	setAttr ".r" -type "double3" 3.0850460586627571 0 0 ;
	setAttr ".s" -type "double3" 0.7290075335738152 0.72900753357381742 0.72900753357382253 ;
createNode nurbsCurve -n "crossShape" -p "shp_leg_bend2_L";
	rename -uid "8CCFBD40-4194-5795-E2D8-0299A8D11E1F";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_bend2_L_pointConstraint1" -p "_shape_leg_bend2_L";
	rename -uid "80DF81D9-41CD-E0F8-1CC3-1AB8E64FF474";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_limb2W0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_leg_limb3W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0.022311447506893067 2.4106226674374662 -0.10310864587298899 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_leg_bend2_L_aimConstraint1" -p "_shape_leg_bend2_L";
	rename -uid "38AE0FE2-4277-1EC8-CE3B-3FB34C5D1B4E";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -2.4490929770573988 -0.011324883343392671 -0.52979989357640134 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_leg_tweak_L" -p "tpl_leg_limb2";
	rename -uid "7F304747-454E-645B-BE32-2C9926B2652D";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.tweak";
createNode transform -n "shp_leg_tweak_L" -p "_shape_leg_tweak_L";
	rename -uid "45CD3C3A-4924-6591-A881-EF868C12AFEF";
	setAttr ".t" -type "double3" 5.5511151231257827e-16 0 1.3877787807814457e-16 ;
	setAttr ".r" -type "double3" 3.0850460586627571 0 0 ;
	setAttr ".s" -type "double3" 0.75747134717451692 0.75747134717451525 0.75747134717451681 ;
createNode nurbsCurve -n "crossShape" -p "shp_leg_tweak_L";
	rename -uid "1CAD81DE-4544-74E9-511A-63AE126CF718";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_tweak_L_pointConstraint1" -p "_shape_leg_tweak_L";
	rename -uid "C986364B-4B40-276F-CA48-AFB14655F3AC";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_limb2W0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_leg_tweak_L_aimConstraint1" -p "_shape_leg_tweak_L";
	rename -uid "70AF721C-4027-7B69-A959-BD85952DB12F";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb3W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" -2.4490929770573997 -0.011324883343392649 -0.52979989357640012 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode joint -n "tpl_leg_clav" -p "tpl_leg";
	rename -uid "2FD6BC5A-42B8-008E-ABE5-0DAB57945727";
	addAttr -ci true -sn "gem_template" -ln "gem_template" -dt "string";
	setAttr ".t" -type "double3" 1.5422139038796163 -0.011713175269000826 2.5783271212498349e-09 ;
	setAttr ".gem_template" -type "string" "clavicle";
createNode transform -n "_shape_leg_ctrls_clavicle_L" -p "tpl_leg_clav";
	rename -uid "400FAADE-4F6B-CFDC-4599-659428449FB9";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.clavicle";
createNode transform -n "shp_leg_ctrls_clavicle_L" -p "_shape_leg_ctrls_clavicle_L";
	rename -uid "F9F411A5-4E2D-DF37-F3F1-3BB99EE2A96E";
	addAttr -ci true -sn "gem_shape_name" -ln "gem_shape_name" -dt "string";
	setAttr ".t" -type "double3" 0 0 4.163336342344337e-17 ;
	setAttr ".gem_shape_name" -type "string" "circle";
createNode nurbsCurve -n "circleShape" -p "shp_leg_ctrls_clavicle_L";
	rename -uid "9D3AAE2C-4A8B-1443-CEAE-81AFDF33B8AF";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 13;
	setAttr ".ovrgb" -type "float3" 0.99142641 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.35354629128316178 -9.7489643541168775e-16 -0.35354629128316184
		-6.0931027213230484e-17 -9.7489643541168775e-16 -0.5
		-0.3535462912831619 -9.7489643541168775e-16 -0.35354629128316184
		-0.50000000000000011 -9.7489643541168775e-16 0
		-0.3535462912831619 -9.7489643541168775e-16 0.35354629128316184
		-6.0931027213230484e-17 -9.7489643541168775e-16 0.5
		0.35354629128316178 -9.7489643541168775e-16 0.35354629128316184
		0.49999999999999994 -9.7489643541168775e-16 0
		0.35354629128316178 -9.7489643541168775e-16 -0.35354629128316184
		-6.0931027213230484e-17 -9.7489643541168775e-16 -0.5
		-0.3535462912831619 -9.7489643541168775e-16 -0.35354629128316184
		;
	setAttr ".gem_color" -type "string" "red";
createNode pointConstraint -n "_shape_leg_ctrls_clavicle_L_pointConstraint1" -p "_shape_leg_ctrls_clavicle_L";
	rename -uid "C22DCCEF-43F2-B185-9E68-FBAA9A278A08";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_leg_clavW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_legW1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" -0.77110695193980827 0.0058565876344989221 -1.2891635675638113e-09 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_leg_ctrls_clavicle_L_aimConstraint1" -p "_shape_leg_ctrls_clavicle_L";
	rename -uid "23D65898-4E76-EF0A-2C80-E5B9B03F9A00";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_legW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" -9.5786324110842499e-08 9.5061585870225898e-08 89.564844667772149 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_leg_limb1_L" -p "tpl_leg";
	rename -uid "8AB8649B-43CF-EEB4-45CB-6B83D00CE3DB";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.limb1";
createNode transform -n "shp_leg_limb1_L" -p "_shape_leg_limb1_L";
	rename -uid "148EBFAB-4CF6-B25C-A506-34BD642B1F00";
	setAttr ".t" -type "double3" -0.062022872166992316 0.24789078140487675 5.5511151231257827e-17 ;
	setAttr ".s" -type "double3" 1.649997321830948 1.6499973218309443 1.6499973218309396 ;
createNode nurbsCurve -n "circleShape" -p "shp_leg_limb1_L";
	rename -uid "25B7DF02-4575-2049-4FDB-2E8680F68FFC";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183318 -2.5460650358232702e-16 -0.53033015584183307
		5.7973881005912261e-17 -2.4115559844801395e-16 -0.7500001570034216
		-0.53033015584183296 -2.5460650358232702e-16 -0.53033015584183307
		-0.75000015700342149 -2.8707986224981054e-16 -2.1733126984620463e-16
		-0.53033015584183296 -3.1955322091729407e-16 0.53033015584183307
		-8.2449740793947898e-17 -3.3300412605160714e-16 0.7500001570034216
		0.53033015584183318 -3.1955322091729407e-16 0.53033015584183307
		0.75000015700342171 -2.8707986224981059e-16 4.0282654572352065e-16
		0.53033015584183318 -2.5460650358232702e-16 -0.53033015584183307
		5.7973881005912261e-17 -2.4115559844801395e-16 -0.7500001570034216
		-0.53033015584183296 -2.5460650358232702e-16 -0.53033015584183307
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_limb1_L_pointConstraint1" -p "_shape_leg_limb1_L";
	rename -uid "239B9041-4F4C-09B6-BBC4-ED8ADAAA4D01";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_legW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".rst" -type "double3" 1.1102230246251565e-16 0 -1.3877787807814457e-17 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_leg_limb1_L_aimConstraint1" -p "_shape_leg_limb1_L";
	rename -uid "34F20C1A-4B3A-0EAA-1E95-9CAD91E9E599";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb2W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 -1 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 0.74329413480293061 0.0034381944028590572 -0.53004551377475373 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_leg_bend1_L" -p "tpl_leg";
	rename -uid "F1B60415-4A5D-2730-E4DA-808A648286D2";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "leg.L::ctrls.bend1";
createNode transform -n "shp_leg_bend1_L" -p "_shape_leg_bend1_L";
	rename -uid "2BF07B0F-4368-DE9A-62CB-15A7DC925D57";
	setAttr ".t" -type "double3" -0.047853740749259965 0 -1.3877787807814457e-16 ;
	setAttr ".r" -type "double3" -1.1697947525654531 0 0 ;
	setAttr ".s" -type "double3" 0.86404621366728473 0.86404621366728396 0.86404621366728185 ;
createNode nurbsCurve -n "crossShape" -p "shp_leg_bend1_L";
	rename -uid "7E275930-4922-254E-016E-26957CDDB708";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 12;
	setAttr ".ovrgb" -type "float3" 0.54296875 0 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1 0 0
		0 0 0
		0 0 1
		0 0 0
		-1 0 0
		0 0 0
		0 0 -1
		;
	setAttr ".gem_color" -type "string" "darkred";
createNode pointConstraint -n "_shape_leg_bend1_L_pointConstraint1" -p "_shape_leg_bend1_L";
	rename -uid "B3AC54AA-490A-F092-990E-FEB4ECF42AEA";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_legW0" -dv 1 -min 0 -at "double";
	addAttr -dcb 0 -ci true -k true -sn "w1" -ln "tpl_leg_limb2W1" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr -s 2 ".tg";
	setAttr ".rst" -type "double3" 0.02226709556850015 2.406711894650396 0.031225192808607263 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
	setAttr -k on ".w1";
createNode aimConstraint -n "_shape_leg_bend1_L_aimConstraint1" -p "_shape_leg_bend1_L";
	rename -uid "BF655064-4CDA-134A-5A9E-48A5BAFE2C23";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_leg_limb2W0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 1;
	setAttr ".rsrr" -type "double3" 0.74329413480293083 0.0034381944028590572 -0.53004551377475362 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_cog" -p "tpl_spine";
	rename -uid "36D28926-4B32-0049-0C95-DAA000B14B73";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.cog";
createNode transform -n "shp_spine_cog" -p "_shape_spine_cog";
	rename -uid "E43E848B-47AD-3DBD-0E7B-ACBD293F340E";
	setAttr ".s" -type "double3" 1.30308812774349 1.30308812774349 1.30308812774349 ;
createNode nurbsCurve -n "circleShape" -p "shp_spine_cog";
	rename -uid "71629305-4F84-CF31-D92D-4DB0F02026DF";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 17;
	setAttr ".ovrgb" -type "float3" 0.99609375 0.99609375 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		1.4142137489115549 8.6595623113289437e-17 -1.4142137489115549
		-2.28176133650648e-16 1.2246470347145754e-16 -2.0000004186757909
		-1.4142137489115549 8.6595623113289437e-17 -1.4142137489115549
		-2.0000004186757909 3.5487207214289884e-32 -5.7955005292321235e-16
		-1.4142137489115549 -8.6595623113289437e-17 1.4142137489115549
		-6.0263912511694185e-16 -1.2246470347145754e-16 2.0000004186757909
		1.4142137489115549 -8.6595623113289437e-17 1.4142137489115549
		2.0000004186757909 -6.5776027167678171e-32 1.0742041219293883e-15
		1.4142137489115549 8.6595623113289437e-17 -1.4142137489115549
		-2.28176133650648e-16 1.2246470347145754e-16 -2.0000004186757909
		-1.4142137489115549 8.6595623113289437e-17 -1.4142137489115549
		;
	setAttr ".gem_color" -type "string" "yellow";
createNode pointConstraint -n "_shape_spine_cog_pointConstraint1" -p "_shape_spine_cog";
	rename -uid "377F0A63-4783-02CA-7D25-D09F5B340DFD";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spineW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_pelvis" -p "tpl_spine";
	rename -uid "E0C98255-4158-F71C-9CC2-35B5348A7E78";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.pelvis";
createNode transform -n "shp_spine_pelvis" -p "_shape_spine_pelvis";
	rename -uid "9EEFBF41-4B9B-54A0-6E06-3E8934AFCB28";
	setAttr ".t" -type "double3" 0 0 -5.5511151231257827e-17 ;
	setAttr ".s" -type "double3" 1.2774412479283535 1.2774412479283535 1.2774412479283535 ;
createNode nurbsCurve -n "crossShape" -p "shp_spine_pelvis";
	rename -uid "A74FD03E-4DEE-BD2F-39C2-22A5E2F2A72F";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 6 0 no 3
		7 0 1 2 3 4 5 6
		7
		1.75 0 0
		0 0 0
		0 0 1.75
		0 0 0
		-1.75 0 0
		0 0 0
		0 0 -1.75
		;
	setAttr ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_spine_pelvis_pointConstraint1" -p "_shape_spine_pelvis";
	rename -uid "6D1C16BF-4D38-6CD3-D9D2-59A33738474C";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spineW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "_shape_spine_pelvis_aimConstraint1" -p "_shape_spine_pelvis";
	rename -uid "79ED6689-4EEE-9E4F-C121-A5B28AE65063";
	addAttr -dcb 0 -ci true -sn "w0" -ln "tpl_spine_hipsW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".wut" 4;
	setAttr ".rsrr" -type "double3" -177.72366345425758 0 0 ;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_spine_pelvisIK" -p "tpl_spine";
	rename -uid "25C74939-4DAD-4EB1-C62C-459C9761E084";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "spine::ctrls.pelvisIK";
createNode transform -n "shp_spine_pelvisIK" -p "_shape_spine_pelvisIK";
	rename -uid "555FBD6D-4B35-FB4A-8FDC-0497097F6630";
	setAttr ".s" -type "double3" 1.2774412479283535 1.2774412479283535 1.2774412479283535 ;
createNode nurbsCurve -n "rhombusShape" -p "shp_spine_pelvisIK";
	rename -uid "7C958D15-461D-A630-CAB0-21B9993972E4";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 17;
	setAttr ".ovrgb" -type "float3" 0.99609375 0.99609375 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 4 0 no 3
		5 0 1 2 3 4
		5
		1.75 0 0
		0 0 -1.75
		-1.75 0 0
		0 0 1.75
		1.75 0 0
		;
	setAttr ".gem_color" -type "string" "yellow";
createNode pointConstraint -n "_shape_spine_pelvisIK_pointConstraint1" -p "_shape_spine_pelvisIK";
	rename -uid "042F85EC-42AF-A665-8D80-67A1A87E4A18";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_spineW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode aimConstraint -n "aimConstraint105" -p "_shape_spine_pelvisIK";
	rename -uid "98EF7216-49F1-6FE5-FBB4-0C8E6A018D17";
	setAttr ".a" -type "double3" 0 1 0 ;
	setAttr ".u" -type "double3" 0 0 0 ;
	setAttr ".hio" yes;
createNode pointConstraint -n "pointConstraint105" -p "_shape_spine_pelvisIK";
	rename -uid "F641B4C9-460A-48E7-3579-65898DF2890D";
	setAttr ".o" -type "double3" 0 1 0 ;
	setAttr ".hio" yes;
createNode transform -n "_shape_world_fly" -p "tpl_world_root";
	rename -uid "8743701C-4739-8942-2DFA-1EB9EA0E9B51";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "world::ctrls.fly";
createNode transform -n "shp_world_fly" -p "_shape_world_fly";
	rename -uid "AC920CE8-4858-AA32-0947-42BE03A9BA66";
	setAttr ".t" -type "double3" 0 0 -3.0390233851704438 ;
	setAttr ".s" -type "double3" 0.68674004977683178 0.68674004977683178 0.68674004977683178 ;
createNode nurbsCurve -n "flyShape" -p "shp_world_fly";
	rename -uid "0D318A00-4239-1EEE-DF0F-A8AE98C5A668";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 8 0 no 3
		9 0 1 2 3 4 5 6 7 8
		9
		0 0 -4.8234158187458958
		-3.750000047627045 0 -1.0734156433419677
		-3.750000047627045 0 -0.0019870924959680316
		-2.6785714625907464 0 -0.0019870924959680316
		3.3644839732860367e-16 0 -2.6805586486732986
		2.6785714625907464 0 -0.0019870924959680316
		3.750000047627045 0 -0.0019870924959680316
		3.750000047627045 0 -1.0734156433419677
		0 0 -4.8234158187458958
		;
	setAttr ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_world_fly_pointConstraint1" -p "_shape_world_fly";
	rename -uid "D2133988-41A6-D0E5-7AE8-74B2EE5CE4D7";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_world_rootW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_world_world" -p "tpl_world";
	rename -uid "61E7B024-4357-1BFF-76D3-F788C98EFF7A";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "world::ctrls.world";
createNode transform -n "shp_world_world" -p "_shape_world_world";
	rename -uid "8DEB7248-4DA4-958E-C865-01B1AC8C802F";
	setAttr ".s" -type "double3" 1.2120165299782071 1.2120165299782071 1.2120165299782071 ;
createNode nurbsCurve -n "circleShape" -p "shp_world_world";
	rename -uid "48FA8D8E-41A3-79A4-BB3F-99B84F94ACE5";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 17;
	setAttr ".ovrgb" -type "float3" 0.99609375 0.99609375 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		3.5355343722788874 2.1648905778322359e-16 -3.5355343722788874
		-5.7044033412662004e-16 3.0616175867864384e-16 -5.0000010466894773
		-3.5355343722788874 2.1648905778322359e-16 -3.5355343722788874
		-5.0000010466894773 8.8718018035724711e-32 -1.4488751323080308e-15
		-3.5355343722788874 -2.1648905778322359e-16 3.5355343722788874
		-1.5065978127923547e-15 -3.0616175867864384e-16 5.0000010466894773
		3.5355343722788874 -2.1648905778322359e-16 3.5355343722788874
		5.0000010466894773 -1.6444006791919542e-31 2.6855103048234711e-15
		3.5355343722788874 2.1648905778322359e-16 -3.5355343722788874
		-5.7044033412662004e-16 3.0616175867864384e-16 -5.0000010466894773
		-3.5355343722788874 2.1648905778322359e-16 -3.5355343722788874
		;
	setAttr ".gem_color" -type "string" "yellow";
createNode pointConstraint -n "_shape_world_world_pointConstraint1" -p "_shape_world_world";
	rename -uid "E8668863-4998-E3AA-FD7A-679AE1264194";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_worldW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_world_move" -p "tpl_world";
	rename -uid "0754CB3E-43F4-69FC-8D37-3087E0ADF1C7";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "world::ctrls.move";
createNode transform -n "shp_world_move" -p "_shape_world_move";
	rename -uid "6E78EB72-4720-43B4-AA1E-B59E0BF43A0D";
	setAttr ".s" -type "double3" 1.2271394347261708 1.2271394347261708 1.2271394347261708 ;
createNode nurbsCurve -n "moveShape" -p "shp_world_move";
	rename -uid "AC2E21D7-494D-7EA8-42AF-DCA59454F1B6";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 16 0 no 3
		17 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
		17
		0 0 3.7499997575536725
		0.74999995151073451 0 2.999999806042938
		0.74999995151073451 0 0.74999995151073451
		2.999999806042938 0 0.74999995151073451
		3.7499997575536725 0 0
		2.999999806042938 0 -0.74999995151073451
		0.74999995151073451 0 -0.74999995151073451
		0.74999995151073451 0 -2.999999806042938
		0 0 -3.7499997575536725
		-0.74999995151073451 0 -2.999999806042938
		-0.74999995151073451 0 -0.74999995151073451
		-2.999999806042938 0 -0.74999995151073451
		-3.7499997575536725 0 0
		-2.999999806042938 0 0.74999995151073451
		-0.74999995151073451 0 0.74999995151073451
		-0.74999995151073451 0 2.999999806042938
		0 0 3.7499997575536725
		;
	setAttr ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_world_move_pointConstraint1" -p "_shape_world_move";
	rename -uid "801076D5-461E-84B8-62B1-60A298CE6494";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_worldW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
createNode transform -n "_shape_world_scale" -p "tpl_world";
	rename -uid "DD300E83-4DC6-8A49-7BF2-B8A091D587F9";
	addAttr -ci true -sn "gem_shape" -ln "gem_shape" -dt "string";
	setAttr ".v" no;
	setAttr ".gem_shape" -type "string" "world::ctrls.scale";
createNode transform -n "shp_world_scale" -p "_shape_world_scale";
	rename -uid "7D0D54AF-4562-21D3-1B76-6E8F33193335";
createNode nurbsCurve -n "scaleShape" -p "shp_world_scale";
	rename -uid "AA6D6B71-4777-502F-F3A1-F9938E7A12C7";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 0.53033015584183307 -8.5283597984046452e-17
		-8.5566050118993011e-17 0.7500001570034216 -1.2060922027520637e-16
		-0.53033015584183307 0.53033015584183307 -8.5283597984046452e-17
		-0.7500001570034216 2.1733126984620463e-16 -3.4949535234365459e-32
		-0.53033015584183307 -0.53033015584183307 8.5283597984046452e-17
		-2.2598967191885318e-16 -0.7500001570034216 1.2060922027520637e-16
		0.53033015584183307 -0.53033015584183307 8.5283597984046452e-17
		0.7500001570034216 -4.0282654572352065e-16 6.477944504401002e-32
		0.53033015584183307 0.53033015584183307 -8.5283597984046452e-17
		-8.5566050118993011e-17 0.7500001570034216 -1.2060922027520637e-16
		-0.53033015584183307 0.53033015584183307 -8.5283597984046452e-17
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape1" -p "shp_world_scale";
	rename -uid "970396E0-4BD5-02FD-3F63-93ADFCB4631F";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		2.6405118538648144e-17 0.53033015584183307 -0.53033015584183307
		-1.2919100360103143e-16 -4.1863300931593242e-16 -0.7500001570034216
		-2.0910879028587859e-16 -0.53033015584183307 -0.53033015584183307
		-1.665334885555362e-16 -0.7500001570034216 3.2468949551499922e-17
		-2.6405118538648144e-17 -0.53033015584183307 0.53033015584183307
		1.2919100360103143e-16 1.0707728727808619e-16 0.7500001570034216
		2.0910879028587859e-16 0.53033015584183307 0.53033015584183307
		1.665334885555362e-16 0.7500001570034216 1.5302630393314988e-16
		2.6405118538648144e-17 0.53033015584183307 -0.53033015584183307
		-1.2919100360103143e-16 -4.1863300931593242e-16 -0.7500001570034216
		-2.0910879028587859e-16 -0.53033015584183307 -0.53033015584183307
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape2" -p "shp_world_scale";
	rename -uid "3D5FC159-4D07-3562-4588-A1AC889DE9D6";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 11;
	setAttr ".ovrgb" -type "float3" 0.33203125 0.1328125 0 ;
	setAttr ".cc" -type "nurbsCurve" 
		3 8 2 no 3
		13 -2 -1 0 1 2 3 4 5 6 7 8 9 10
		11
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-0.7500001570034216 1.3307702705358707e-32 -2.1733126984620463e-16
		-0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		-2.2598967191885318e-16 -4.5924263801796575e-17 0.7500001570034216
		0.53033015584183307 -3.2473358667483541e-17 0.53033015584183307
		0.7500001570034216 -2.4666010187879316e-32 4.0282654572352065e-16
		0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		-8.5566050118993011e-17 4.5924263801796575e-17 -0.7500001570034216
		-0.53033015584183307 3.2473358667483541e-17 -0.53033015584183307
		;
	setAttr -k on ".gem_color" -type "string" "#520";
createNode nurbsCurve -n "scaleShape3" -p "shp_world_scale";
	rename -uid "46C8394B-4CC0-CF0A-64C1-54BF5B09A234";
	addAttr -ci true -sn "width" -ln "width" -dv 0.10000000149011612 -at "float";
	addAttr -ci true -k true -sn "gem_color" -ln "gem_color" -dt "string";
	setAttr -k off ".v";
	setAttr ".ove" yes;
	setAttr ".ovrgbf" yes;
	setAttr ".ovc" 10;
	setAttr ".ovrgb" -type "float3" 0.54296875 0.26953125 0.07421875 ;
	setAttr ".cc" -type "nurbsCurve" 
		1 7 0 no 3
		8 0 1 2 3 4 5 6 7
		8
		0 -0.67677680983654498 0
		0 0.67677680983654498 0
		0 0 0
		0 0 0.67677680983654498
		0 0 -0.67677680983654498
		0 0 0
		-0.67677680983654498 0 0
		0.67677680983654498 0 0
		;
	setAttr -k on ".gem_color" -type "string" "saddlebrown";
createNode pointConstraint -n "_shape_world_scale_pointConstraint1" -p "_shape_world_scale";
	rename -uid "6762EE6A-44E5-5D39-F358-0B8089508F4B";
	addAttr -dcb 0 -ci true -k true -sn "w0" -ln "tpl_worldW0" -dv 1 -min 0 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".hio" yes;
	setAttr -k on ".w0";
select -ne :time1;
	setAttr -av -k on ".cch";
	setAttr -av -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".o" 5;
	setAttr -av -k on ".unw" 5;
	setAttr -av -k on ".etw";
	setAttr -av -k on ".tps";
	setAttr -av -k on ".tms";
select -ne :hardwareRenderingGlobals;
	setAttr -av -k on ".ihi";
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr -av ".ta";
	setAttr -av ".tq";
	setAttr -av ".aoam";
	setAttr -av ".aora";
	setAttr -av ".hfd";
	setAttr -av ".hfe";
	setAttr -av ".hfa";
	setAttr -av ".mbe";
	setAttr -av -k on ".mbsof";
	setAttr ".fprt" yes;
select -ne :renderPartition;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".st";
	setAttr -cb on ".an";
	setAttr -cb on ".pt";
select -ne :renderGlobalsList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
select -ne :defaultShaderList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 5 ".s";
select -ne :postProcessList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
	setAttr -k on ".ihi";
	setAttr -s 6 ".r";
select -ne :initialShadingGroup;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr -k on ".ro" yes;
select -ne :initialParticleSE;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr -k on ".ro" yes;
select -ne :defaultRenderGlobals;
	addAttr -ci true -h true -sn "dss" -ln "defaultSurfaceShader" -dt "string";
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -av -k on ".macc";
	setAttr -av -k on ".macd";
	setAttr -av -k on ".macq";
	setAttr -av -k on ".mcfr";
	setAttr -cb on ".ifg";
	setAttr -av -k on ".clip";
	setAttr -av -k on ".edm";
	setAttr -av -k on ".edl";
	setAttr -av -cb on ".ren";
	setAttr -av -k on ".esr";
	setAttr -av -k on ".ors";
	setAttr -cb on ".sdf";
	setAttr -av -k on ".outf";
	setAttr -av -cb on ".imfkey";
	setAttr -av -k on ".gama";
	setAttr -av -k on ".an";
	setAttr -cb on ".ar";
	setAttr -k on ".fs";
	setAttr -k on ".ef";
	setAttr -av -k on ".bfs";
	setAttr -cb on ".me";
	setAttr -cb on ".se";
	setAttr -av -k on ".be";
	setAttr -av -cb on ".ep";
	setAttr -av -k on ".fec";
	setAttr -av -k on ".ofc";
	setAttr -cb on ".ofe";
	setAttr -cb on ".efe";
	setAttr -cb on ".oft";
	setAttr -cb on ".umfn";
	setAttr -cb on ".ufe";
	setAttr -av -k on ".pff";
	setAttr -av -k on ".peie";
	setAttr -av -k on ".ifp";
	setAttr -k on ".rv";
	setAttr -av -k on ".comp";
	setAttr -av -k on ".cth";
	setAttr -av -k on ".soll";
	setAttr -cb on ".sosl";
	setAttr -av -k on ".rd";
	setAttr -av -k on ".lp";
	setAttr -av -k on ".sp";
	setAttr -av -k on ".shs";
	setAttr -av -k on ".lpr";
	setAttr -cb on ".gv";
	setAttr -cb on ".sv";
	setAttr -av -k on ".mm";
	setAttr -av -k on ".npu";
	setAttr -av -k on ".itf";
	setAttr -av -k on ".shp";
	setAttr -cb on ".isp";
	setAttr -av -k on ".uf";
	setAttr -av -k on ".oi";
	setAttr -av -k on ".rut";
	setAttr -av -k on ".mot";
	setAttr -av -k on ".mb";
	setAttr -av -k on ".mbf";
	setAttr -av -k on ".mbso";
	setAttr -av -k on ".mbsc";
	setAttr -av -k on ".afp";
	setAttr -av -k on ".pfb";
	setAttr -k on ".pram";
	setAttr -k on ".poam";
	setAttr -k on ".prlm";
	setAttr -k on ".polm";
	setAttr -cb on ".prm";
	setAttr -cb on ".pom";
	setAttr -cb on ".pfrm";
	setAttr -cb on ".pfom";
	setAttr -av -k on ".bll";
	setAttr -av -k on ".bls";
	setAttr -av -k on ".smv";
	setAttr -av -k on ".ubc";
	setAttr -av -k on ".mbc";
	setAttr -cb on ".mbt";
	setAttr -av -k on ".udbx";
	setAttr -av -k on ".smc";
	setAttr -av -k on ".kmv";
	setAttr -cb on ".isl";
	setAttr -cb on ".ism";
	setAttr -cb on ".imb";
	setAttr -av -k on ".rlen";
	setAttr -av -k on ".frts";
	setAttr -av -k on ".tlwd";
	setAttr -av -k on ".tlht";
	setAttr -av -k on ".jfc";
	setAttr -cb on ".rsb";
	setAttr -av -k on ".ope";
	setAttr -av -k on ".oppf";
	setAttr -av -k on ".rcp";
	setAttr -av -k on ".icp";
	setAttr -av -k on ".ocp";
	setAttr -cb on ".hbl";
	setAttr ".dss" -type "string" "lambert1";
select -ne :defaultResolution;
	setAttr -av -k on ".cch";
	setAttr -av -k on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -k on ".bnm";
	setAttr -av -k on ".w";
	setAttr -av -k on ".h";
	setAttr -av -k on ".pa" 1;
	setAttr -av -k on ".al";
	setAttr -av -k on ".dar";
	setAttr -av -k on ".ldar";
	setAttr -av -cb on ".dpi";
	setAttr -av -k on ".off";
	setAttr -av -k on ".fld";
	setAttr -av -k on ".zsl";
	setAttr -av -cb on ".isu";
	setAttr -av -cb on ".pdu";
select -ne :defaultColorMgtGlobals;
	setAttr ".cfe" yes;
	setAttr ".cfp" -type "string" "//srv-bin/bin/ocio/aces/ctr_renderman.ocio";
	setAttr ".vtn" -type "string" "sRGB (ACES)";
	setAttr ".vn" -type "string" "sRGB";
	setAttr ".dn" -type "string" "ACES";
	setAttr ".wsn" -type "string" "ACES - ACEScg";
	setAttr ".ovt" no;
	setAttr ".povt" no;
	setAttr ".otn" -type "string" "sRGB (ACES)";
	setAttr ".potn" -type "string" "sRGB (ACES)";
select -ne :hardwareRenderGlobals;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k off -cb on ".ctrs" 256;
	setAttr -av -k off -cb on ".btrs" 512;
	setAttr -k off -cb on ".fbfm";
	setAttr -k off -cb on ".ehql";
	setAttr -k off -cb on ".eams";
	setAttr -k off -cb on ".eeaa";
	setAttr -k off -cb on ".engm";
	setAttr -k off -cb on ".mes";
	setAttr -k off -cb on ".emb";
	setAttr -av -k off -cb on ".mbbf";
	setAttr -k off -cb on ".mbs";
	setAttr -k off -cb on ".trm";
	setAttr -k off -cb on ".tshc";
	setAttr -k off -cb on ".enpt";
	setAttr -k off -cb on ".clmt";
	setAttr -k off -cb on ".tcov";
	setAttr -k off -cb on ".lith";
	setAttr -k off -cb on ".sobc";
	setAttr -k off -cb on ".cuth";
	setAttr -k off -cb on ".hgcd";
	setAttr -k off -cb on ".hgci";
	setAttr -k off -cb on ".mgcs";
	setAttr -k off -cb on ".twa";
	setAttr -k off -cb on ".twz";
	setAttr -k on ".hwcc";
	setAttr -k on ".hwdp";
	setAttr -k on ".hwql";
	setAttr -k on ".hwfr";
	setAttr -k on ".soll";
	setAttr -k on ".sosl";
	setAttr -k on ".bswa";
	setAttr -k on ".shml";
	setAttr -k on ".hwel";
select -ne :ikSystem;
	setAttr -k on ".cch";
	setAttr -k on ".ihi";
	setAttr -k on ".nds";
	setAttr -k on ".bnm";
	setAttr -av -k on ".gsn";
	setAttr -k on ".gsv";
	setAttr -s 4 ".sol";
connectAttr "tpl_spine.s" "tpl_spine_chain1.is";
connectAttr "tpl_spine_chain1.s" "tpl_spine_chain2.is";
connectAttr "tpl_spine_chain2.s" "tpl_spine_tip.is";
connectAttr "_shape_arm_digits_L_pointConstraint1.ctx" "_shape_arm_digits_L.tx";
connectAttr "_shape_arm_digits_L_pointConstraint1.cty" "_shape_arm_digits_L.ty";
connectAttr "_shape_arm_digits_L_pointConstraint1.ctz" "_shape_arm_digits_L.tz";
connectAttr "_shape_arm_digits_L_aimConstraint1.crx" "_shape_arm_digits_L.rx";
connectAttr "_shape_arm_digits_L_aimConstraint1.cry" "_shape_arm_digits_L.ry";
connectAttr "_shape_arm_digits_L_aimConstraint1.crz" "_shape_arm_digits_L.rz";
connectAttr "_shape_arm_digits_L.pim" "_shape_arm_digits_L_pointConstraint1.cpim"
		;
connectAttr "_shape_arm_digits_L.rp" "_shape_arm_digits_L_pointConstraint1.crp";
connectAttr "_shape_arm_digits_L.rpt" "_shape_arm_digits_L_pointConstraint1.crt"
		;
connectAttr "tpl_arm_digits.t" "_shape_arm_digits_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_digits.rp" "_shape_arm_digits_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_arm_digits.rpt" "_shape_arm_digits_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_arm_digits.pm" "_shape_arm_digits_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_arm_digits_L_pointConstraint1.w0" "_shape_arm_digits_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_digits_L.pim" "_shape_arm_digits_L_aimConstraint1.cpim";
connectAttr "_shape_arm_digits_L.t" "_shape_arm_digits_L_aimConstraint1.ct";
connectAttr "_shape_arm_digits_L.rp" "_shape_arm_digits_L_aimConstraint1.crp";
connectAttr "_shape_arm_digits_L.rpt" "_shape_arm_digits_L_aimConstraint1.crt";
connectAttr "_shape_arm_digits_L.ro" "_shape_arm_digits_L_aimConstraint1.cro";
connectAttr "tpl_arm_tip.t" "_shape_arm_digits_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_tip.rp" "_shape_arm_digits_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_tip.rpt" "_shape_arm_digits_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_tip.pm" "_shape_arm_digits_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_digits_L_aimConstraint1.w0" "_shape_arm_digits_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_limb3.wm" "_shape_arm_digits_L_aimConstraint1.wum";
connectAttr "_shape_arm_ik_L_pointConstraint1.ctx" "_shape_arm_ik_L.tx";
connectAttr "_shape_arm_ik_L_pointConstraint1.cty" "_shape_arm_ik_L.ty";
connectAttr "_shape_arm_ik_L_pointConstraint1.ctz" "_shape_arm_ik_L.tz";
connectAttr "_shape_arm_ik_L_aimConstraint1.crx" "_shape_arm_ik_L.rx";
connectAttr "_shape_arm_ik_L_aimConstraint1.cry" "_shape_arm_ik_L.ry";
connectAttr "_shape_arm_ik_L_aimConstraint1.crz" "_shape_arm_ik_L.rz";
connectAttr "_shape_arm_ik_L.pim" "_shape_arm_ik_L_pointConstraint1.cpim";
connectAttr "_shape_arm_ik_L.rp" "_shape_arm_ik_L_pointConstraint1.crp";
connectAttr "_shape_arm_ik_L.rpt" "_shape_arm_ik_L_pointConstraint1.crt";
connectAttr "tpl_arm_digits.t" "_shape_arm_ik_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_digits.rp" "_shape_arm_ik_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm_digits.rpt" "_shape_arm_ik_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm_digits.pm" "_shape_arm_ik_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_ik_L_pointConstraint1.w0" "_shape_arm_ik_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_ik_L.pim" "_shape_arm_ik_L_aimConstraint1.cpim";
connectAttr "_shape_arm_ik_L.t" "_shape_arm_ik_L_aimConstraint1.ct";
connectAttr "_shape_arm_ik_L.rp" "_shape_arm_ik_L_aimConstraint1.crp";
connectAttr "_shape_arm_ik_L.rpt" "_shape_arm_ik_L_aimConstraint1.crt";
connectAttr "_shape_arm_ik_L.ro" "_shape_arm_ik_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb3.t" "_shape_arm_ik_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_ik_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_ik_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_ik_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_ik_L_aimConstraint1.w0" "_shape_arm_ik_L_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_pointConstraint1.ctx" "_shape_arm_ctrls_ik_offset_L.tx"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_pointConstraint1.cty" "_shape_arm_ctrls_ik_offset_L.ty"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_pointConstraint1.ctz" "_shape_arm_ctrls_ik_offset_L.tz"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_aimConstraint1.crx" "_shape_arm_ctrls_ik_offset_L.rx"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_aimConstraint1.cry" "_shape_arm_ctrls_ik_offset_L.ry"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_aimConstraint1.crz" "_shape_arm_ctrls_ik_offset_L.rz"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.pim" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.cpim"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.rp" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.crp"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.rpt" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.crt"
		;
connectAttr "tpl_arm_digits.t" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_arm_digits.rp" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_arm_digits.rpt" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_arm_digits.pm" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_pointConstraint1.w0" "_shape_arm_ctrls_ik_offset_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.pim" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.cpim"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.t" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.ct"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.rp" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.crp"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.rpt" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.crt"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L.ro" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.cro"
		;
connectAttr "tpl_arm_limb3.t" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.tg[0].tt"
		;
connectAttr "tpl_arm_limb3.rp" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.tg[0].trp"
		;
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.tg[0].trt"
		;
connectAttr "tpl_arm_limb3.pm" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.tg[0].tpm"
		;
connectAttr "_shape_arm_ctrls_ik_offset_L_aimConstraint1.w0" "_shape_arm_ctrls_ik_offset_L_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_limb3_L_pointConstraint1.ctx" "_shape_arm_limb3_L.tx";
connectAttr "_shape_arm_limb3_L_pointConstraint1.cty" "_shape_arm_limb3_L.ty";
connectAttr "_shape_arm_limb3_L_pointConstraint1.ctz" "_shape_arm_limb3_L.tz";
connectAttr "_shape_arm_limb3_L_aimConstraint1.crx" "_shape_arm_limb3_L.rx";
connectAttr "_shape_arm_limb3_L_aimConstraint1.cry" "_shape_arm_limb3_L.ry";
connectAttr "_shape_arm_limb3_L_aimConstraint1.crz" "_shape_arm_limb3_L.rz";
connectAttr "_shape_arm_limb3_L.pim" "_shape_arm_limb3_L_pointConstraint1.cpim";
connectAttr "_shape_arm_limb3_L.rp" "_shape_arm_limb3_L_pointConstraint1.crp";
connectAttr "_shape_arm_limb3_L.rpt" "_shape_arm_limb3_L_pointConstraint1.crt";
connectAttr "tpl_arm_limb3.t" "_shape_arm_limb3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_limb3_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_limb3_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_limb3_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb3_L_pointConstraint1.w0" "_shape_arm_limb3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_limb3_L.pim" "_shape_arm_limb3_L_aimConstraint1.cpim";
connectAttr "_shape_arm_limb3_L.t" "_shape_arm_limb3_L_aimConstraint1.ct";
connectAttr "_shape_arm_limb3_L.rp" "_shape_arm_limb3_L_aimConstraint1.crp";
connectAttr "_shape_arm_limb3_L.rpt" "_shape_arm_limb3_L_aimConstraint1.crt";
connectAttr "_shape_arm_limb3_L.ro" "_shape_arm_limb3_L_aimConstraint1.cro";
connectAttr "tpl_arm_digits.t" "_shape_arm_limb3_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_digits.rp" "_shape_arm_limb3_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_digits.rpt" "_shape_arm_limb3_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_digits.pm" "_shape_arm_limb3_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb3_L_aimConstraint1.w0" "_shape_arm_limb3_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_tip.wm" "_shape_arm_limb3_L_aimConstraint1.wum";
connectAttr "tpl_arm_limb3.s" "tpl_fingers.is";
connectAttr "tpl_fingers.s" "tpl_thumb.is";
connectAttr "tpl_thumb.s" "tpl_thumb_chain1.is";
connectAttr "tpl_thumb_chain1.s" "tpl_thumb_chain2.is";
connectAttr "tpl_thumb_chain2.s" "tpl_thumb_tip.is";
connectAttr "_shape_thumb_2_L_pointConstraint1.ctx" "_shape_thumb_2_L.tx";
connectAttr "_shape_thumb_2_L_pointConstraint1.cty" "_shape_thumb_2_L.ty";
connectAttr "_shape_thumb_2_L_pointConstraint1.ctz" "_shape_thumb_2_L.tz";
connectAttr "_shape_thumb_2_L.pim" "_shape_thumb_2_L_pointConstraint1.cpim";
connectAttr "_shape_thumb_2_L.rp" "_shape_thumb_2_L_pointConstraint1.crp";
connectAttr "_shape_thumb_2_L.rpt" "_shape_thumb_2_L_pointConstraint1.crt";
connectAttr "tpl_thumb_chain2.t" "_shape_thumb_2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_thumb_chain2.rp" "_shape_thumb_2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_thumb_chain2.rpt" "_shape_thumb_2_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_thumb_chain2.pm" "_shape_thumb_2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_thumb_2_L_pointConstraint1.w0" "_shape_thumb_2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_thumb_tip.t" "_shape_thumb_2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_thumb_tip.rp" "_shape_thumb_2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_thumb_tip.rpt" "_shape_thumb_2_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_thumb_tip.pm" "_shape_thumb_2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_thumb_2_L_pointConstraint1.w1" "_shape_thumb_2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_thumb_1_L_pointConstraint1.ctx" "_shape_thumb_1_L.tx";
connectAttr "_shape_thumb_1_L_pointConstraint1.cty" "_shape_thumb_1_L.ty";
connectAttr "_shape_thumb_1_L_pointConstraint1.ctz" "_shape_thumb_1_L.tz";
connectAttr "_shape_thumb_1_L.pim" "_shape_thumb_1_L_pointConstraint1.cpim";
connectAttr "_shape_thumb_1_L.rp" "_shape_thumb_1_L_pointConstraint1.crp";
connectAttr "_shape_thumb_1_L.rpt" "_shape_thumb_1_L_pointConstraint1.crt";
connectAttr "tpl_thumb_chain1.t" "_shape_thumb_1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_thumb_chain1.rp" "_shape_thumb_1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_thumb_chain1.rpt" "_shape_thumb_1_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_thumb_chain1.pm" "_shape_thumb_1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_thumb_1_L_pointConstraint1.w0" "_shape_thumb_1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_thumb_chain2.t" "_shape_thumb_1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_thumb_chain2.rp" "_shape_thumb_1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_thumb_chain2.rpt" "_shape_thumb_1_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_thumb_chain2.pm" "_shape_thumb_1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_thumb_1_L_pointConstraint1.w1" "_shape_thumb_1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_thumb_0_L_pointConstraint1.ctx" "_shape_thumb_0_L.tx";
connectAttr "_shape_thumb_0_L_pointConstraint1.cty" "_shape_thumb_0_L.ty";
connectAttr "_shape_thumb_0_L_pointConstraint1.ctz" "_shape_thumb_0_L.tz";
connectAttr "_shape_thumb_0_L.pim" "_shape_thumb_0_L_pointConstraint1.cpim";
connectAttr "_shape_thumb_0_L.rp" "_shape_thumb_0_L_pointConstraint1.crp";
connectAttr "_shape_thumb_0_L.rpt" "_shape_thumb_0_L_pointConstraint1.crt";
connectAttr "tpl_thumb.t" "_shape_thumb_0_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_thumb.rp" "_shape_thumb_0_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_thumb.rpt" "_shape_thumb_0_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_thumb.pm" "_shape_thumb_0_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_thumb_0_L_pointConstraint1.w0" "_shape_thumb_0_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_thumb_chain1.t" "_shape_thumb_0_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_thumb_chain1.rp" "_shape_thumb_0_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_thumb_chain1.rpt" "_shape_thumb_0_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_thumb_chain1.pm" "_shape_thumb_0_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_thumb_0_L_pointConstraint1.w1" "_shape_thumb_0_L_pointConstraint1.tg[1].tw"
		;
connectAttr "tpl_fingers.s" "tpl_point.is";
connectAttr "tpl_point.s" "tpl_point_chain1.is";
connectAttr "tpl_point_chain1.s" "tpl_point_chain2.is";
connectAttr "tpl_point_chain2.s" "tpl_point_chain3.is";
connectAttr "tpl_point_chain3.s" "tpl_point_tip.is";
connectAttr "_shape_point_3_L_pointConstraint1.ctx" "_shape_point_3_L.tx";
connectAttr "_shape_point_3_L_pointConstraint1.cty" "_shape_point_3_L.ty";
connectAttr "_shape_point_3_L_pointConstraint1.ctz" "_shape_point_3_L.tz";
connectAttr "_shape_point_3_L.pim" "_shape_point_3_L_pointConstraint1.cpim";
connectAttr "_shape_point_3_L.rp" "_shape_point_3_L_pointConstraint1.crp";
connectAttr "_shape_point_3_L.rpt" "_shape_point_3_L_pointConstraint1.crt";
connectAttr "tpl_point_chain3.t" "_shape_point_3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_point_chain3.rp" "_shape_point_3_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_point_chain3.rpt" "_shape_point_3_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_point_chain3.pm" "_shape_point_3_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_point_3_L_pointConstraint1.w0" "_shape_point_3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_point_tip.t" "_shape_point_3_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_point_tip.rp" "_shape_point_3_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_point_tip.rpt" "_shape_point_3_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_point_tip.pm" "_shape_point_3_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_point_3_L_pointConstraint1.w1" "_shape_point_3_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_point_2_L_pointConstraint1.ctx" "_shape_point_2_L.tx";
connectAttr "_shape_point_2_L_pointConstraint1.cty" "_shape_point_2_L.ty";
connectAttr "_shape_point_2_L_pointConstraint1.ctz" "_shape_point_2_L.tz";
connectAttr "_shape_point_2_L.pim" "_shape_point_2_L_pointConstraint1.cpim";
connectAttr "_shape_point_2_L.rp" "_shape_point_2_L_pointConstraint1.crp";
connectAttr "_shape_point_2_L.rpt" "_shape_point_2_L_pointConstraint1.crt";
connectAttr "tpl_point_chain2.t" "_shape_point_2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_point_chain2.rp" "_shape_point_2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_point_chain2.rpt" "_shape_point_2_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_point_chain2.pm" "_shape_point_2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_point_2_L_pointConstraint1.w0" "_shape_point_2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_point_chain3.t" "_shape_point_2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_point_chain3.rp" "_shape_point_2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_point_chain3.rpt" "_shape_point_2_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_point_chain3.pm" "_shape_point_2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_point_2_L_pointConstraint1.w1" "_shape_point_2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_point_1_L_pointConstraint1.ctx" "_shape_point_1_L.tx";
connectAttr "_shape_point_1_L_pointConstraint1.cty" "_shape_point_1_L.ty";
connectAttr "_shape_point_1_L_pointConstraint1.ctz" "_shape_point_1_L.tz";
connectAttr "_shape_point_1_L.pim" "_shape_point_1_L_pointConstraint1.cpim";
connectAttr "_shape_point_1_L.rp" "_shape_point_1_L_pointConstraint1.crp";
connectAttr "_shape_point_1_L.rpt" "_shape_point_1_L_pointConstraint1.crt";
connectAttr "tpl_point_chain1.t" "_shape_point_1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_point_chain1.rp" "_shape_point_1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_point_chain1.rpt" "_shape_point_1_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_point_chain1.pm" "_shape_point_1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_point_1_L_pointConstraint1.w0" "_shape_point_1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_point_chain2.t" "_shape_point_1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_point_chain2.rp" "_shape_point_1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_point_chain2.rpt" "_shape_point_1_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_point_chain2.pm" "_shape_point_1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_point_1_L_pointConstraint1.w1" "_shape_point_1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_point_0_L_pointConstraint1.ctx" "_shape_point_0_L.tx";
connectAttr "_shape_point_0_L_pointConstraint1.cty" "_shape_point_0_L.ty";
connectAttr "_shape_point_0_L_pointConstraint1.ctz" "_shape_point_0_L.tz";
connectAttr "_shape_point_0_L.pim" "_shape_point_0_L_pointConstraint1.cpim";
connectAttr "_shape_point_0_L.rp" "_shape_point_0_L_pointConstraint1.crp";
connectAttr "_shape_point_0_L.rpt" "_shape_point_0_L_pointConstraint1.crt";
connectAttr "tpl_point.t" "_shape_point_0_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_point.rp" "_shape_point_0_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_point.rpt" "_shape_point_0_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_point.pm" "_shape_point_0_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_point_0_L_pointConstraint1.w0" "_shape_point_0_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_point_chain1.t" "_shape_point_0_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_point_chain1.rp" "_shape_point_0_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_point_chain1.rpt" "_shape_point_0_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_point_chain1.pm" "_shape_point_0_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_point_0_L_pointConstraint1.w1" "_shape_point_0_L_pointConstraint1.tg[1].tw"
		;
connectAttr "tpl_fingers.s" "tpl_middle.is";
connectAttr "tpl_middle.s" "tpl_middle_chain1.is";
connectAttr "tpl_middle_chain1.s" "tpl_middle_chain2.is";
connectAttr "tpl_middle_chain2.s" "tpl_middle_chain3.is";
connectAttr "tpl_middle_chain3.s" "tpl_middle_tip.is";
connectAttr "_shape_middle_3_L_pointConstraint1.ctx" "_shape_middle_3_L.tx";
connectAttr "_shape_middle_3_L_pointConstraint1.cty" "_shape_middle_3_L.ty";
connectAttr "_shape_middle_3_L_pointConstraint1.ctz" "_shape_middle_3_L.tz";
connectAttr "_shape_middle_3_L.pim" "_shape_middle_3_L_pointConstraint1.cpim";
connectAttr "_shape_middle_3_L.rp" "_shape_middle_3_L_pointConstraint1.crp";
connectAttr "_shape_middle_3_L.rpt" "_shape_middle_3_L_pointConstraint1.crt";
connectAttr "tpl_middle_chain3.t" "_shape_middle_3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_middle_chain3.rp" "_shape_middle_3_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_middle_chain3.rpt" "_shape_middle_3_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_middle_chain3.pm" "_shape_middle_3_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_middle_3_L_pointConstraint1.w0" "_shape_middle_3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_middle_tip.t" "_shape_middle_3_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_middle_tip.rp" "_shape_middle_3_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_middle_tip.rpt" "_shape_middle_3_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_middle_tip.pm" "_shape_middle_3_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_middle_3_L_pointConstraint1.w1" "_shape_middle_3_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_middle_2_L_pointConstraint1.ctx" "_shape_middle_2_L.tx";
connectAttr "_shape_middle_2_L_pointConstraint1.cty" "_shape_middle_2_L.ty";
connectAttr "_shape_middle_2_L_pointConstraint1.ctz" "_shape_middle_2_L.tz";
connectAttr "_shape_middle_2_L.pim" "_shape_middle_2_L_pointConstraint1.cpim";
connectAttr "_shape_middle_2_L.rp" "_shape_middle_2_L_pointConstraint1.crp";
connectAttr "_shape_middle_2_L.rpt" "_shape_middle_2_L_pointConstraint1.crt";
connectAttr "tpl_middle_chain2.t" "_shape_middle_2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_middle_chain2.rp" "_shape_middle_2_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_middle_chain2.rpt" "_shape_middle_2_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_middle_chain2.pm" "_shape_middle_2_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_middle_2_L_pointConstraint1.w0" "_shape_middle_2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_middle_chain3.t" "_shape_middle_2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_middle_chain3.rp" "_shape_middle_2_L_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_middle_chain3.rpt" "_shape_middle_2_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_middle_chain3.pm" "_shape_middle_2_L_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_middle_2_L_pointConstraint1.w1" "_shape_middle_2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_middle_1_L_pointConstraint1.ctx" "_shape_middle_1_L.tx";
connectAttr "_shape_middle_1_L_pointConstraint1.cty" "_shape_middle_1_L.ty";
connectAttr "_shape_middle_1_L_pointConstraint1.ctz" "_shape_middle_1_L.tz";
connectAttr "_shape_middle_1_L.pim" "_shape_middle_1_L_pointConstraint1.cpim";
connectAttr "_shape_middle_1_L.rp" "_shape_middle_1_L_pointConstraint1.crp";
connectAttr "_shape_middle_1_L.rpt" "_shape_middle_1_L_pointConstraint1.crt";
connectAttr "tpl_middle_chain1.t" "_shape_middle_1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_middle_chain1.rp" "_shape_middle_1_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_middle_chain1.rpt" "_shape_middle_1_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_middle_chain1.pm" "_shape_middle_1_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_middle_1_L_pointConstraint1.w0" "_shape_middle_1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_middle_chain2.t" "_shape_middle_1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_middle_chain2.rp" "_shape_middle_1_L_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_middle_chain2.rpt" "_shape_middle_1_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_middle_chain2.pm" "_shape_middle_1_L_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_middle_1_L_pointConstraint1.w1" "_shape_middle_1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_middle_0_L_pointConstraint1.ctx" "_shape_middle_0_L.tx";
connectAttr "_shape_middle_0_L_pointConstraint1.cty" "_shape_middle_0_L.ty";
connectAttr "_shape_middle_0_L_pointConstraint1.ctz" "_shape_middle_0_L.tz";
connectAttr "_shape_middle_0_L.pim" "_shape_middle_0_L_pointConstraint1.cpim";
connectAttr "_shape_middle_0_L.rp" "_shape_middle_0_L_pointConstraint1.crp";
connectAttr "_shape_middle_0_L.rpt" "_shape_middle_0_L_pointConstraint1.crt";
connectAttr "tpl_middle.t" "_shape_middle_0_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_middle.rp" "_shape_middle_0_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_middle.rpt" "_shape_middle_0_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_middle.pm" "_shape_middle_0_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_middle_0_L_pointConstraint1.w0" "_shape_middle_0_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_middle_chain1.t" "_shape_middle_0_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_middle_chain1.rp" "_shape_middle_0_L_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_middle_chain1.rpt" "_shape_middle_0_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_middle_chain1.pm" "_shape_middle_0_L_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_middle_0_L_pointConstraint1.w1" "_shape_middle_0_L_pointConstraint1.tg[1].tw"
		;
connectAttr "tpl_fingers.s" "tpl_ring.is";
connectAttr "tpl_ring.s" "tpl_ring_chain1.is";
connectAttr "tpl_ring_chain1.s" "tpl_ring_chain2.is";
connectAttr "tpl_ring_chain2.s" "tpl_ring_chain3.is";
connectAttr "tpl_ring_chain3.s" "tpl_ring_tip.is";
connectAttr "_shape_ring_3_L_pointConstraint1.ctx" "_shape_ring_3_L.tx";
connectAttr "_shape_ring_3_L_pointConstraint1.cty" "_shape_ring_3_L.ty";
connectAttr "_shape_ring_3_L_pointConstraint1.ctz" "_shape_ring_3_L.tz";
connectAttr "_shape_ring_3_L.pim" "_shape_ring_3_L_pointConstraint1.cpim";
connectAttr "_shape_ring_3_L.rp" "_shape_ring_3_L_pointConstraint1.crp";
connectAttr "_shape_ring_3_L.rpt" "_shape_ring_3_L_pointConstraint1.crt";
connectAttr "tpl_ring_chain3.t" "_shape_ring_3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_ring_chain3.rp" "_shape_ring_3_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_ring_chain3.rpt" "_shape_ring_3_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_ring_chain3.pm" "_shape_ring_3_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_ring_3_L_pointConstraint1.w0" "_shape_ring_3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_ring_tip.t" "_shape_ring_3_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_ring_tip.rp" "_shape_ring_3_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_ring_tip.rpt" "_shape_ring_3_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_ring_tip.pm" "_shape_ring_3_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_ring_3_L_pointConstraint1.w1" "_shape_ring_3_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_ring_2_L_pointConstraint1.ctx" "_shape_ring_2_L.tx";
connectAttr "_shape_ring_2_L_pointConstraint1.cty" "_shape_ring_2_L.ty";
connectAttr "_shape_ring_2_L_pointConstraint1.ctz" "_shape_ring_2_L.tz";
connectAttr "_shape_ring_2_L.pim" "_shape_ring_2_L_pointConstraint1.cpim";
connectAttr "_shape_ring_2_L.rp" "_shape_ring_2_L_pointConstraint1.crp";
connectAttr "_shape_ring_2_L.rpt" "_shape_ring_2_L_pointConstraint1.crt";
connectAttr "tpl_ring_chain2.t" "_shape_ring_2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_ring_chain2.rp" "_shape_ring_2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_ring_chain2.rpt" "_shape_ring_2_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_ring_chain2.pm" "_shape_ring_2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_ring_2_L_pointConstraint1.w0" "_shape_ring_2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_ring_chain3.t" "_shape_ring_2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_ring_chain3.rp" "_shape_ring_2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_ring_chain3.rpt" "_shape_ring_2_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_ring_chain3.pm" "_shape_ring_2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_ring_2_L_pointConstraint1.w1" "_shape_ring_2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_ring_1_L_pointConstraint1.ctx" "_shape_ring_1_L.tx";
connectAttr "_shape_ring_1_L_pointConstraint1.cty" "_shape_ring_1_L.ty";
connectAttr "_shape_ring_1_L_pointConstraint1.ctz" "_shape_ring_1_L.tz";
connectAttr "_shape_ring_1_L.pim" "_shape_ring_1_L_pointConstraint1.cpim";
connectAttr "_shape_ring_1_L.rp" "_shape_ring_1_L_pointConstraint1.crp";
connectAttr "_shape_ring_1_L.rpt" "_shape_ring_1_L_pointConstraint1.crt";
connectAttr "tpl_ring_chain1.t" "_shape_ring_1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_ring_chain1.rp" "_shape_ring_1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_ring_chain1.rpt" "_shape_ring_1_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_ring_chain1.pm" "_shape_ring_1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_ring_1_L_pointConstraint1.w0" "_shape_ring_1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_ring_chain2.t" "_shape_ring_1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_ring_chain2.rp" "_shape_ring_1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_ring_chain2.rpt" "_shape_ring_1_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_ring_chain2.pm" "_shape_ring_1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_ring_1_L_pointConstraint1.w1" "_shape_ring_1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_ring_0_L_pointConstraint1.ctx" "_shape_ring_0_L.tx";
connectAttr "_shape_ring_0_L_pointConstraint1.cty" "_shape_ring_0_L.ty";
connectAttr "_shape_ring_0_L_pointConstraint1.ctz" "_shape_ring_0_L.tz";
connectAttr "_shape_ring_0_L.pim" "_shape_ring_0_L_pointConstraint1.cpim";
connectAttr "_shape_ring_0_L.rp" "_shape_ring_0_L_pointConstraint1.crp";
connectAttr "_shape_ring_0_L.rpt" "_shape_ring_0_L_pointConstraint1.crt";
connectAttr "tpl_ring.t" "_shape_ring_0_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_ring.rp" "_shape_ring_0_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_ring.rpt" "_shape_ring_0_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_ring.pm" "_shape_ring_0_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_ring_0_L_pointConstraint1.w0" "_shape_ring_0_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_ring_chain1.t" "_shape_ring_0_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_ring_chain1.rp" "_shape_ring_0_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_ring_chain1.rpt" "_shape_ring_0_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_ring_chain1.pm" "_shape_ring_0_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_ring_0_L_pointConstraint1.w1" "_shape_ring_0_L_pointConstraint1.tg[1].tw"
		;
connectAttr "tpl_fingers.s" "tpl_pinky.is";
connectAttr "tpl_pinky.s" "tpl_pinky_chain1.is";
connectAttr "tpl_pinky_chain1.s" "tpl_pinky_chain2.is";
connectAttr "tpl_pinky_chain2.s" "tpl_pinky_chain3.is";
connectAttr "tpl_pinky_chain3.s" "tpl_pinky_tip.is";
connectAttr "_shape_pinky_3_L_pointConstraint1.ctx" "_shape_pinky_3_L.tx";
connectAttr "_shape_pinky_3_L_pointConstraint1.cty" "_shape_pinky_3_L.ty";
connectAttr "_shape_pinky_3_L_pointConstraint1.ctz" "_shape_pinky_3_L.tz";
connectAttr "_shape_pinky_3_L.pim" "_shape_pinky_3_L_pointConstraint1.cpim";
connectAttr "_shape_pinky_3_L.rp" "_shape_pinky_3_L_pointConstraint1.crp";
connectAttr "_shape_pinky_3_L.rpt" "_shape_pinky_3_L_pointConstraint1.crt";
connectAttr "tpl_pinky_chain3.t" "_shape_pinky_3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_pinky_chain3.rp" "_shape_pinky_3_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_pinky_chain3.rpt" "_shape_pinky_3_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_pinky_chain3.pm" "_shape_pinky_3_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_pinky_3_L_pointConstraint1.w0" "_shape_pinky_3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_pinky_tip.t" "_shape_pinky_3_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_pinky_tip.rp" "_shape_pinky_3_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_pinky_tip.rpt" "_shape_pinky_3_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_pinky_tip.pm" "_shape_pinky_3_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_pinky_3_L_pointConstraint1.w1" "_shape_pinky_3_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_pinky_2_L_pointConstraint1.ctx" "_shape_pinky_2_L.tx";
connectAttr "_shape_pinky_2_L_pointConstraint1.cty" "_shape_pinky_2_L.ty";
connectAttr "_shape_pinky_2_L_pointConstraint1.ctz" "_shape_pinky_2_L.tz";
connectAttr "_shape_pinky_2_L.pim" "_shape_pinky_2_L_pointConstraint1.cpim";
connectAttr "_shape_pinky_2_L.rp" "_shape_pinky_2_L_pointConstraint1.crp";
connectAttr "_shape_pinky_2_L.rpt" "_shape_pinky_2_L_pointConstraint1.crt";
connectAttr "tpl_pinky_chain2.t" "_shape_pinky_2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_pinky_chain2.rp" "_shape_pinky_2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_pinky_chain2.rpt" "_shape_pinky_2_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_pinky_chain2.pm" "_shape_pinky_2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_pinky_2_L_pointConstraint1.w0" "_shape_pinky_2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_pinky_chain3.t" "_shape_pinky_2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_pinky_chain3.rp" "_shape_pinky_2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_pinky_chain3.rpt" "_shape_pinky_2_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_pinky_chain3.pm" "_shape_pinky_2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_pinky_2_L_pointConstraint1.w1" "_shape_pinky_2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_pinky_1_L_pointConstraint1.ctx" "_shape_pinky_1_L.tx";
connectAttr "_shape_pinky_1_L_pointConstraint1.cty" "_shape_pinky_1_L.ty";
connectAttr "_shape_pinky_1_L_pointConstraint1.ctz" "_shape_pinky_1_L.tz";
connectAttr "_shape_pinky_1_L.pim" "_shape_pinky_1_L_pointConstraint1.cpim";
connectAttr "_shape_pinky_1_L.rp" "_shape_pinky_1_L_pointConstraint1.crp";
connectAttr "_shape_pinky_1_L.rpt" "_shape_pinky_1_L_pointConstraint1.crt";
connectAttr "tpl_pinky_chain1.t" "_shape_pinky_1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_pinky_chain1.rp" "_shape_pinky_1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_pinky_chain1.rpt" "_shape_pinky_1_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_pinky_chain1.pm" "_shape_pinky_1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_pinky_1_L_pointConstraint1.w0" "_shape_pinky_1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_pinky_chain2.t" "_shape_pinky_1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_pinky_chain2.rp" "_shape_pinky_1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_pinky_chain2.rpt" "_shape_pinky_1_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_pinky_chain2.pm" "_shape_pinky_1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_pinky_1_L_pointConstraint1.w1" "_shape_pinky_1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_pinky_0_L_pointConstraint1.ctx" "_shape_pinky_0_L.tx";
connectAttr "_shape_pinky_0_L_pointConstraint1.cty" "_shape_pinky_0_L.ty";
connectAttr "_shape_pinky_0_L_pointConstraint1.ctz" "_shape_pinky_0_L.tz";
connectAttr "_shape_pinky_0_L.pim" "_shape_pinky_0_L_pointConstraint1.cpim";
connectAttr "_shape_pinky_0_L.rp" "_shape_pinky_0_L_pointConstraint1.crp";
connectAttr "_shape_pinky_0_L.rpt" "_shape_pinky_0_L_pointConstraint1.crt";
connectAttr "tpl_pinky.t" "_shape_pinky_0_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_pinky.rp" "_shape_pinky_0_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_pinky.rpt" "_shape_pinky_0_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_pinky.pm" "_shape_pinky_0_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_pinky_0_L_pointConstraint1.w0" "_shape_pinky_0_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_pinky_chain1.t" "_shape_pinky_0_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_pinky_chain1.rp" "_shape_pinky_0_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_pinky_chain1.rpt" "_shape_pinky_0_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_pinky_chain1.pm" "_shape_pinky_0_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_pinky_0_L_pointConstraint1.w1" "_shape_pinky_0_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_arm_limb2_L_pointConstraint1.ctx" "_shape_arm_limb2_L.tx";
connectAttr "_shape_arm_limb2_L_pointConstraint1.cty" "_shape_arm_limb2_L.ty";
connectAttr "_shape_arm_limb2_L_pointConstraint1.ctz" "_shape_arm_limb2_L.tz";
connectAttr "_shape_arm_limb2_L_aimConstraint1.crx" "_shape_arm_limb2_L.rx";
connectAttr "_shape_arm_limb2_L_aimConstraint1.cry" "_shape_arm_limb2_L.ry";
connectAttr "_shape_arm_limb2_L_aimConstraint1.crz" "_shape_arm_limb2_L.rz";
connectAttr "_shape_arm_limb2_L.pim" "_shape_arm_limb2_L_pointConstraint1.cpim";
connectAttr "_shape_arm_limb2_L.rp" "_shape_arm_limb2_L_pointConstraint1.crp";
connectAttr "_shape_arm_limb2_L.rpt" "_shape_arm_limb2_L_pointConstraint1.crt";
connectAttr "tpl_arm_limb2.t" "_shape_arm_limb2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_limb2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_limb2_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_limb2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb2_L_pointConstraint1.w0" "_shape_arm_limb2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_limb2_L.pim" "_shape_arm_limb2_L_aimConstraint1.cpim";
connectAttr "_shape_arm_limb2_L.t" "_shape_arm_limb2_L_aimConstraint1.ct";
connectAttr "_shape_arm_limb2_L.rp" "_shape_arm_limb2_L_aimConstraint1.crp";
connectAttr "_shape_arm_limb2_L.rpt" "_shape_arm_limb2_L_aimConstraint1.crt";
connectAttr "_shape_arm_limb2_L.ro" "_shape_arm_limb2_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb3.t" "_shape_arm_limb2_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_limb2_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_limb2_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_limb2_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb2_L_aimConstraint1.w0" "_shape_arm_limb2_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm.wm" "_shape_arm_limb2_L_aimConstraint1.wum";
connectAttr "_shape_arm_bend2_L_pointConstraint1.ctx" "_shape_arm_bend2_L.tx";
connectAttr "_shape_arm_bend2_L_pointConstraint1.cty" "_shape_arm_bend2_L.ty";
connectAttr "_shape_arm_bend2_L_pointConstraint1.ctz" "_shape_arm_bend2_L.tz";
connectAttr "_shape_arm_bend2_L_aimConstraint1.crx" "_shape_arm_bend2_L.rx";
connectAttr "_shape_arm_bend2_L_aimConstraint1.cry" "_shape_arm_bend2_L.ry";
connectAttr "_shape_arm_bend2_L_aimConstraint1.crz" "_shape_arm_bend2_L.rz";
connectAttr "_shape_arm_bend2_L.pim" "_shape_arm_bend2_L_pointConstraint1.cpim";
connectAttr "_shape_arm_bend2_L.rp" "_shape_arm_bend2_L_pointConstraint1.crp";
connectAttr "_shape_arm_bend2_L.rpt" "_shape_arm_bend2_L_pointConstraint1.crt";
connectAttr "tpl_arm_limb2.t" "_shape_arm_bend2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_bend2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_bend2_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_bend2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_bend2_L_pointConstraint1.w0" "_shape_arm_bend2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_limb3.t" "_shape_arm_bend2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_bend2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_bend2_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_bend2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_arm_bend2_L_pointConstraint1.w1" "_shape_arm_bend2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_arm_bend2_L.pim" "_shape_arm_bend2_L_aimConstraint1.cpim";
connectAttr "_shape_arm_bend2_L.t" "_shape_arm_bend2_L_aimConstraint1.ct";
connectAttr "_shape_arm_bend2_L.rp" "_shape_arm_bend2_L_aimConstraint1.crp";
connectAttr "_shape_arm_bend2_L.rpt" "_shape_arm_bend2_L_aimConstraint1.crt";
connectAttr "_shape_arm_bend2_L.ro" "_shape_arm_bend2_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb3.t" "_shape_arm_bend2_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_bend2_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_bend2_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_bend2_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_bend2_L_aimConstraint1.w0" "_shape_arm_bend2_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm.wm" "_shape_arm_bend2_L_aimConstraint1.wum";
connectAttr "_shape_arm_tweak_L_pointConstraint1.ctx" "_shape_arm_tweak_L.tx";
connectAttr "_shape_arm_tweak_L_pointConstraint1.cty" "_shape_arm_tweak_L.ty";
connectAttr "_shape_arm_tweak_L_pointConstraint1.ctz" "_shape_arm_tweak_L.tz";
connectAttr "_shape_arm_tweak_L_aimConstraint1.crx" "_shape_arm_tweak_L.rx";
connectAttr "_shape_arm_tweak_L_aimConstraint1.cry" "_shape_arm_tweak_L.ry";
connectAttr "_shape_arm_tweak_L_aimConstraint1.crz" "_shape_arm_tweak_L.rz";
connectAttr "_shape_arm_tweak_L.pim" "_shape_arm_tweak_L_pointConstraint1.cpim";
connectAttr "_shape_arm_tweak_L.rp" "_shape_arm_tweak_L_pointConstraint1.crp";
connectAttr "_shape_arm_tweak_L.rpt" "_shape_arm_tweak_L_pointConstraint1.crt";
connectAttr "tpl_arm_limb2.t" "_shape_arm_tweak_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_tweak_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_tweak_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_tweak_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_tweak_L_pointConstraint1.w0" "_shape_arm_tweak_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_tweak_L.pim" "_shape_arm_tweak_L_aimConstraint1.cpim";
connectAttr "_shape_arm_tweak_L.t" "_shape_arm_tweak_L_aimConstraint1.ct";
connectAttr "_shape_arm_tweak_L.rp" "_shape_arm_tweak_L_aimConstraint1.crp";
connectAttr "_shape_arm_tweak_L.rpt" "_shape_arm_tweak_L_aimConstraint1.crt";
connectAttr "_shape_arm_tweak_L.ro" "_shape_arm_tweak_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb3.t" "_shape_arm_tweak_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb3.rp" "_shape_arm_tweak_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb3.rpt" "_shape_arm_tweak_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb3.pm" "_shape_arm_tweak_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_tweak_L_aimConstraint1.w0" "_shape_arm_tweak_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm.wm" "_shape_arm_tweak_L_aimConstraint1.wum";
connectAttr "_shape_arm_clavicle_L_pointConstraint1.ctx" "_shape_arm_clavicle_L.tx"
		;
connectAttr "_shape_arm_clavicle_L_pointConstraint1.cty" "_shape_arm_clavicle_L.ty"
		;
connectAttr "_shape_arm_clavicle_L_pointConstraint1.ctz" "_shape_arm_clavicle_L.tz"
		;
connectAttr "_shape_arm_clavicle_L_aimConstraint1.crx" "_shape_arm_clavicle_L.rx"
		;
connectAttr "_shape_arm_clavicle_L_aimConstraint1.cry" "_shape_arm_clavicle_L.ry"
		;
connectAttr "_shape_arm_clavicle_L_aimConstraint1.crz" "_shape_arm_clavicle_L.rz"
		;
connectAttr "_shape_arm_clavicle_L.pim" "_shape_arm_clavicle_L_pointConstraint1.cpim"
		;
connectAttr "_shape_arm_clavicle_L.rp" "_shape_arm_clavicle_L_pointConstraint1.crp"
		;
connectAttr "_shape_arm_clavicle_L.rpt" "_shape_arm_clavicle_L_pointConstraint1.crt"
		;
connectAttr "tpl_arm_clav.t" "_shape_arm_clavicle_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm_clav.rp" "_shape_arm_clavicle_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_arm_clav.rpt" "_shape_arm_clavicle_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_arm_clav.pm" "_shape_arm_clavicle_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_arm_clavicle_L_pointConstraint1.w0" "_shape_arm_clavicle_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm.t" "_shape_arm_clavicle_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_arm.rp" "_shape_arm_clavicle_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_arm.rpt" "_shape_arm_clavicle_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_arm.pm" "_shape_arm_clavicle_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_arm_clavicle_L_pointConstraint1.w1" "_shape_arm_clavicle_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_arm_clavicle_L.pim" "_shape_arm_clavicle_L_aimConstraint1.cpim"
		;
connectAttr "_shape_arm_clavicle_L.t" "_shape_arm_clavicle_L_aimConstraint1.ct";
connectAttr "_shape_arm_clavicle_L.rp" "_shape_arm_clavicle_L_aimConstraint1.crp"
		;
connectAttr "_shape_arm_clavicle_L.rpt" "_shape_arm_clavicle_L_aimConstraint1.crt"
		;
connectAttr "_shape_arm_clavicle_L.ro" "_shape_arm_clavicle_L_aimConstraint1.cro"
		;
connectAttr "tpl_arm.t" "_shape_arm_clavicle_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm.rp" "_shape_arm_clavicle_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm.rpt" "_shape_arm_clavicle_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm.pm" "_shape_arm_clavicle_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_clavicle_L_aimConstraint1.w0" "_shape_arm_clavicle_L_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_limb1_L_pointConstraint1.ctx" "_shape_arm_limb1_L.tx";
connectAttr "_shape_arm_limb1_L_pointConstraint1.cty" "_shape_arm_limb1_L.ty";
connectAttr "_shape_arm_limb1_L_pointConstraint1.ctz" "_shape_arm_limb1_L.tz";
connectAttr "_shape_arm_limb1_L_aimConstraint1.crx" "_shape_arm_limb1_L.rx";
connectAttr "_shape_arm_limb1_L_aimConstraint1.cry" "_shape_arm_limb1_L.ry";
connectAttr "_shape_arm_limb1_L_aimConstraint1.crz" "_shape_arm_limb1_L.rz";
connectAttr "_shape_arm_limb1_L.pim" "_shape_arm_limb1_L_pointConstraint1.cpim";
connectAttr "_shape_arm_limb1_L.rp" "_shape_arm_limb1_L_pointConstraint1.crp";
connectAttr "_shape_arm_limb1_L.rpt" "_shape_arm_limb1_L_pointConstraint1.crt";
connectAttr "tpl_arm.t" "_shape_arm_limb1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm.rp" "_shape_arm_limb1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm.rpt" "_shape_arm_limb1_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm.pm" "_shape_arm_limb1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb1_L_pointConstraint1.w0" "_shape_arm_limb1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_arm_limb1_L.pim" "_shape_arm_limb1_L_aimConstraint1.cpim";
connectAttr "_shape_arm_limb1_L.t" "_shape_arm_limb1_L_aimConstraint1.ct";
connectAttr "_shape_arm_limb1_L.rp" "_shape_arm_limb1_L_aimConstraint1.crp";
connectAttr "_shape_arm_limb1_L.rpt" "_shape_arm_limb1_L_aimConstraint1.crt";
connectAttr "_shape_arm_limb1_L.ro" "_shape_arm_limb1_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb2.t" "_shape_arm_limb1_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_limb1_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_limb1_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_limb1_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_limb1_L_aimConstraint1.w0" "_shape_arm_limb1_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_limb3.wm" "_shape_arm_limb1_L_aimConstraint1.wum";
connectAttr "_shape_arm_bend1_L_pointConstraint1.ctx" "_shape_arm_bend1_L.tx";
connectAttr "_shape_arm_bend1_L_pointConstraint1.cty" "_shape_arm_bend1_L.ty";
connectAttr "_shape_arm_bend1_L_pointConstraint1.ctz" "_shape_arm_bend1_L.tz";
connectAttr "_shape_arm_bend1_L_aimConstraint1.crx" "_shape_arm_bend1_L.rx";
connectAttr "_shape_arm_bend1_L_aimConstraint1.cry" "_shape_arm_bend1_L.ry";
connectAttr "_shape_arm_bend1_L_aimConstraint1.crz" "_shape_arm_bend1_L.rz";
connectAttr "_shape_arm_bend1_L.pim" "_shape_arm_bend1_L_pointConstraint1.cpim";
connectAttr "_shape_arm_bend1_L.rp" "_shape_arm_bend1_L_pointConstraint1.crp";
connectAttr "_shape_arm_bend1_L.rpt" "_shape_arm_bend1_L_pointConstraint1.crt";
connectAttr "tpl_arm.t" "_shape_arm_bend1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_arm.rp" "_shape_arm_bend1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_arm.rpt" "_shape_arm_bend1_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_arm.pm" "_shape_arm_bend1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_arm_bend1_L_pointConstraint1.w0" "_shape_arm_bend1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_limb2.t" "_shape_arm_bend1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_bend1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_bend1_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_bend1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_arm_bend1_L_pointConstraint1.w1" "_shape_arm_bend1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_arm_bend1_L.pim" "_shape_arm_bend1_L_aimConstraint1.cpim";
connectAttr "_shape_arm_bend1_L.t" "_shape_arm_bend1_L_aimConstraint1.ct";
connectAttr "_shape_arm_bend1_L.rp" "_shape_arm_bend1_L_aimConstraint1.crp";
connectAttr "_shape_arm_bend1_L.rpt" "_shape_arm_bend1_L_aimConstraint1.crt";
connectAttr "_shape_arm_bend1_L.ro" "_shape_arm_bend1_L_aimConstraint1.cro";
connectAttr "tpl_arm_limb2.t" "_shape_arm_bend1_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_arm_limb2.rp" "_shape_arm_bend1_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_arm_limb2.rpt" "_shape_arm_bend1_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_arm_limb2.pm" "_shape_arm_bend1_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_arm_bend1_L_aimConstraint1.w0" "_shape_arm_bend1_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_arm_limb3.wm" "_shape_arm_bend1_L_aimConstraint1.wum";
connectAttr "tpl_neck.s" "tpl_neck_head.is";
connectAttr "tpl_neck_head.s" "tpl_neck_tip.is";
connectAttr "_shape_neck_head_pointConstraint1.ctx" "_shape_neck_head.tx";
connectAttr "_shape_neck_head_pointConstraint1.cty" "_shape_neck_head.ty";
connectAttr "_shape_neck_head_pointConstraint1.ctz" "_shape_neck_head.tz";
connectAttr "_shape_neck_head_aimConstraint1.crx" "_shape_neck_head.rx";
connectAttr "_shape_neck_head_aimConstraint1.cry" "_shape_neck_head.ry";
connectAttr "_shape_neck_head_aimConstraint1.crz" "_shape_neck_head.rz";
connectAttr "_shape_neck_head.pim" "_shape_neck_head_pointConstraint1.cpim";
connectAttr "_shape_neck_head.rp" "_shape_neck_head_pointConstraint1.crp";
connectAttr "_shape_neck_head.rpt" "_shape_neck_head_pointConstraint1.crt";
connectAttr "tpl_neck_head.t" "_shape_neck_head_pointConstraint1.tg[0].tt";
connectAttr "tpl_neck_head.rp" "_shape_neck_head_pointConstraint1.tg[0].trp";
connectAttr "tpl_neck_head.rpt" "_shape_neck_head_pointConstraint1.tg[0].trt";
connectAttr "tpl_neck_head.pm" "_shape_neck_head_pointConstraint1.tg[0].tpm";
connectAttr "_shape_neck_head_pointConstraint1.w0" "_shape_neck_head_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_neck_tip.t" "_shape_neck_head_pointConstraint1.tg[1].tt";
connectAttr "tpl_neck_tip.rp" "_shape_neck_head_pointConstraint1.tg[1].trp";
connectAttr "tpl_neck_tip.rpt" "_shape_neck_head_pointConstraint1.tg[1].trt";
connectAttr "tpl_neck_tip.pm" "_shape_neck_head_pointConstraint1.tg[1].tpm";
connectAttr "_shape_neck_head_pointConstraint1.w1" "_shape_neck_head_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_neck_head.pim" "_shape_neck_head_aimConstraint1.cpim";
connectAttr "_shape_neck_head.t" "_shape_neck_head_aimConstraint1.ct";
connectAttr "_shape_neck_head.rp" "_shape_neck_head_aimConstraint1.crp";
connectAttr "_shape_neck_head.rpt" "_shape_neck_head_aimConstraint1.crt";
connectAttr "_shape_neck_head.ro" "_shape_neck_head_aimConstraint1.cro";
connectAttr "tpl_neck_tip.t" "_shape_neck_head_aimConstraint1.tg[0].tt";
connectAttr "tpl_neck_tip.rp" "_shape_neck_head_aimConstraint1.tg[0].trp";
connectAttr "tpl_neck_tip.rpt" "_shape_neck_head_aimConstraint1.tg[0].trt";
connectAttr "tpl_neck_tip.pm" "_shape_neck_head_aimConstraint1.tg[0].tpm";
connectAttr "_shape_neck_head_aimConstraint1.w0" "_shape_neck_head_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_neck_scale_pointConstraint1.ctx" "_shape_neck_scale.tx";
connectAttr "_shape_neck_scale_pointConstraint1.cty" "_shape_neck_scale.ty";
connectAttr "_shape_neck_scale_pointConstraint1.ctz" "_shape_neck_scale.tz";
connectAttr "_shape_neck_scale.pim" "_shape_neck_scale_pointConstraint1.cpim";
connectAttr "_shape_neck_scale.rp" "_shape_neck_scale_pointConstraint1.crp";
connectAttr "_shape_neck_scale.rpt" "_shape_neck_scale_pointConstraint1.crt";
connectAttr "tpl_neck_head.t" "_shape_neck_scale_pointConstraint1.tg[0].tt";
connectAttr "tpl_neck_head.rp" "_shape_neck_scale_pointConstraint1.tg[0].trp";
connectAttr "tpl_neck_head.rpt" "_shape_neck_scale_pointConstraint1.tg[0].trt";
connectAttr "tpl_neck_head.pm" "_shape_neck_scale_pointConstraint1.tg[0].tpm";
connectAttr "_shape_neck_scale_pointConstraint1.w0" "_shape_neck_scale_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_neck_mid_pointConstraint1.ctx" "_shape_neck_mid.tx";
connectAttr "_shape_neck_mid_pointConstraint1.cty" "_shape_neck_mid.ty";
connectAttr "_shape_neck_mid_pointConstraint1.ctz" "_shape_neck_mid.tz";
connectAttr "_shape_neck_mid_aimConstraint1.crx" "_shape_neck_mid.rx";
connectAttr "_shape_neck_mid_aimConstraint1.cry" "_shape_neck_mid.ry";
connectAttr "_shape_neck_mid_aimConstraint1.crz" "_shape_neck_mid.rz";
connectAttr "_shape_neck_mid.pim" "_shape_neck_mid_pointConstraint1.cpim";
connectAttr "_shape_neck_mid.rp" "_shape_neck_mid_pointConstraint1.crp";
connectAttr "_shape_neck_mid.rpt" "_shape_neck_mid_pointConstraint1.crt";
connectAttr "tpl_neck.t" "_shape_neck_mid_pointConstraint1.tg[0].tt";
connectAttr "tpl_neck.rp" "_shape_neck_mid_pointConstraint1.tg[0].trp";
connectAttr "tpl_neck.rpt" "_shape_neck_mid_pointConstraint1.tg[0].trt";
connectAttr "tpl_neck.pm" "_shape_neck_mid_pointConstraint1.tg[0].tpm";
connectAttr "_shape_neck_mid_pointConstraint1.w0" "_shape_neck_mid_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_neck_head.t" "_shape_neck_mid_pointConstraint1.tg[1].tt";
connectAttr "tpl_neck_head.rp" "_shape_neck_mid_pointConstraint1.tg[1].trp";
connectAttr "tpl_neck_head.rpt" "_shape_neck_mid_pointConstraint1.tg[1].trt";
connectAttr "tpl_neck_head.pm" "_shape_neck_mid_pointConstraint1.tg[1].tpm";
connectAttr "_shape_neck_mid_pointConstraint1.w1" "_shape_neck_mid_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_neck_mid.pim" "_shape_neck_mid_aimConstraint1.cpim";
connectAttr "_shape_neck_mid.t" "_shape_neck_mid_aimConstraint1.ct";
connectAttr "_shape_neck_mid.rp" "_shape_neck_mid_aimConstraint1.crp";
connectAttr "_shape_neck_mid.rpt" "_shape_neck_mid_aimConstraint1.crt";
connectAttr "_shape_neck_mid.ro" "_shape_neck_mid_aimConstraint1.cro";
connectAttr "tpl_neck_head.t" "_shape_neck_mid_aimConstraint1.tg[0].tt";
connectAttr "tpl_neck_head.rp" "_shape_neck_mid_aimConstraint1.tg[0].trp";
connectAttr "tpl_neck_head.rpt" "_shape_neck_mid_aimConstraint1.tg[0].trt";
connectAttr "tpl_neck_head.pm" "_shape_neck_mid_aimConstraint1.tg[0].tpm";
connectAttr "_shape_neck_mid_aimConstraint1.w0" "_shape_neck_mid_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_neck_neck0_pointConstraint1.ctx" "_shape_neck_neck0.tx";
connectAttr "_shape_neck_neck0_pointConstraint1.cty" "_shape_neck_neck0.ty";
connectAttr "_shape_neck_neck0_pointConstraint1.ctz" "_shape_neck_neck0.tz";
connectAttr "_shape_neck_neck0_aimConstraint1.crx" "_shape_neck_neck0.rx";
connectAttr "_shape_neck_neck0_aimConstraint1.cry" "_shape_neck_neck0.ry";
connectAttr "_shape_neck_neck0_aimConstraint1.crz" "_shape_neck_neck0.rz";
connectAttr "_shape_neck_neck0.pim" "_shape_neck_neck0_pointConstraint1.cpim";
connectAttr "_shape_neck_neck0.rp" "_shape_neck_neck0_pointConstraint1.crp";
connectAttr "_shape_neck_neck0.rpt" "_shape_neck_neck0_pointConstraint1.crt";
connectAttr "tpl_neck.t" "_shape_neck_neck0_pointConstraint1.tg[0].tt";
connectAttr "tpl_neck.rp" "_shape_neck_neck0_pointConstraint1.tg[0].trp";
connectAttr "tpl_neck.rpt" "_shape_neck_neck0_pointConstraint1.tg[0].trt";
connectAttr "tpl_neck.pm" "_shape_neck_neck0_pointConstraint1.tg[0].tpm";
connectAttr "_shape_neck_neck0_pointConstraint1.w0" "_shape_neck_neck0_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_neck_neck0.pim" "_shape_neck_neck0_aimConstraint1.cpim";
connectAttr "_shape_neck_neck0.t" "_shape_neck_neck0_aimConstraint1.ct";
connectAttr "_shape_neck_neck0.rp" "_shape_neck_neck0_aimConstraint1.crp";
connectAttr "_shape_neck_neck0.rpt" "_shape_neck_neck0_aimConstraint1.crt";
connectAttr "_shape_neck_neck0.ro" "_shape_neck_neck0_aimConstraint1.cro";
connectAttr "tpl_neck_head.t" "_shape_neck_neck0_aimConstraint1.tg[0].tt";
connectAttr "tpl_neck_head.rp" "_shape_neck_neck0_aimConstraint1.tg[0].trp";
connectAttr "tpl_neck_head.rpt" "_shape_neck_neck0_aimConstraint1.tg[0].trt";
connectAttr "tpl_neck_head.pm" "_shape_neck_neck0_aimConstraint1.tg[0].tpm";
connectAttr "_shape_neck_neck0_aimConstraint1.w0" "_shape_neck_neck0_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_neck_ctrls_head_offset_pointConstraint1.ctx" "_shape_neck_ctrls_head_offset.tx"
		;
connectAttr "_shape_neck_ctrls_head_offset_pointConstraint1.cty" "_shape_neck_ctrls_head_offset.ty"
		;
connectAttr "_shape_neck_ctrls_head_offset_pointConstraint1.ctz" "_shape_neck_ctrls_head_offset.tz"
		;
connectAttr "_shape_neck_ctrls_head_offset_aimConstraint1.crx" "_shape_neck_ctrls_head_offset.rx"
		;
connectAttr "_shape_neck_ctrls_head_offset_aimConstraint1.cry" "_shape_neck_ctrls_head_offset.ry"
		;
connectAttr "_shape_neck_ctrls_head_offset_aimConstraint1.crz" "_shape_neck_ctrls_head_offset.rz"
		;
connectAttr "_shape_neck_ctrls_head_offset.pim" "_shape_neck_ctrls_head_offset_pointConstraint1.cpim"
		;
connectAttr "_shape_neck_ctrls_head_offset.rp" "_shape_neck_ctrls_head_offset_pointConstraint1.crp"
		;
connectAttr "_shape_neck_ctrls_head_offset.rpt" "_shape_neck_ctrls_head_offset_pointConstraint1.crt"
		;
connectAttr "tpl_neck_head.t" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_neck_head.rp" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_neck_head.rpt" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_neck_head.pm" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_neck_ctrls_head_offset_pointConstraint1.w0" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_neck_tip.t" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[1].tt"
		;
connectAttr "tpl_neck_tip.rp" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_neck_tip.rpt" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_neck_tip.pm" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_neck_ctrls_head_offset_pointConstraint1.w1" "_shape_neck_ctrls_head_offset_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_neck_ctrls_head_offset.pim" "_shape_neck_ctrls_head_offset_aimConstraint1.cpim"
		;
connectAttr "_shape_neck_ctrls_head_offset.t" "_shape_neck_ctrls_head_offset_aimConstraint1.ct"
		;
connectAttr "_shape_neck_ctrls_head_offset.rp" "_shape_neck_ctrls_head_offset_aimConstraint1.crp"
		;
connectAttr "_shape_neck_ctrls_head_offset.rpt" "_shape_neck_ctrls_head_offset_aimConstraint1.crt"
		;
connectAttr "_shape_neck_ctrls_head_offset.ro" "_shape_neck_ctrls_head_offset_aimConstraint1.cro"
		;
connectAttr "tpl_neck_tip.t" "_shape_neck_ctrls_head_offset_aimConstraint1.tg[0].tt"
		;
connectAttr "tpl_neck_tip.rp" "_shape_neck_ctrls_head_offset_aimConstraint1.tg[0].trp"
		;
connectAttr "tpl_neck_tip.rpt" "_shape_neck_ctrls_head_offset_aimConstraint1.tg[0].trt"
		;
connectAttr "tpl_neck_tip.pm" "_shape_neck_ctrls_head_offset_aimConstraint1.tg[0].tpm"
		;
connectAttr "_shape_neck_ctrls_head_offset_aimConstraint1.w0" "_shape_neck_ctrls_head_offset_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_spineIK_pointConstraint1.ctx" "_shape_spine_spineIK.tx"
		;
connectAttr "_shape_spine_spineIK_pointConstraint1.cty" "_shape_spine_spineIK.ty"
		;
connectAttr "_shape_spine_spineIK_pointConstraint1.ctz" "_shape_spine_spineIK.tz"
		;
connectAttr "aimConstraint106.crx" "_shape_spine_spineIK.rx";
connectAttr "aimConstraint106.cry" "_shape_spine_spineIK.ry";
connectAttr "aimConstraint106.crz" "_shape_spine_spineIK.rz";
connectAttr "_shape_spine_spineIK.pim" "_shape_spine_spineIK_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_spineIK.rp" "_shape_spine_spineIK_pointConstraint1.crp"
		;
connectAttr "_shape_spine_spineIK.rpt" "_shape_spine_spineIK_pointConstraint1.crt"
		;
connectAttr "tpl_spine_tip.t" "_shape_spine_spineIK_pointConstraint1.tg[0].tt";
connectAttr "tpl_spine_tip.rp" "_shape_spine_spineIK_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_spine_tip.rpt" "_shape_spine_spineIK_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_spine_tip.pm" "_shape_spine_spineIK_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_spine_spineIK_pointConstraint1.w0" "_shape_spine_spineIK_pointConstraint1.tg[0].tw"
		;
connectAttr "pointConstraint106.ct" "aimConstraint106.tg[0].tt";
connectAttr "_shape_spine_spineIK.pim" "aimConstraint106.cpim";
connectAttr "tpl_spine_tip.t" "pointConstraint106.tg[0].tt";
connectAttr "tpl_spine_tip.pm" "pointConstraint106.tg[0].tpm";
connectAttr "_shape_spine_spine2_pointConstraint1.ctx" "_shape_spine_spine2.tx";
connectAttr "_shape_spine_spine2_pointConstraint1.cty" "_shape_spine_spine2.ty";
connectAttr "_shape_spine_spine2_pointConstraint1.ctz" "_shape_spine_spine2.tz";
connectAttr "_shape_spine_spine2.pim" "_shape_spine_spine2_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_spine2.rp" "_shape_spine_spine2_pointConstraint1.crp";
connectAttr "_shape_spine_spine2.rpt" "_shape_spine_spine2_pointConstraint1.crt"
		;
connectAttr "tpl_spine_chain2.t" "_shape_spine_spine2_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_spine_chain2.rp" "_shape_spine_spine2_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_spine_chain2.rpt" "_shape_spine_spine2_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_spine_chain2.pm" "_shape_spine_spine2_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_spine_spine2_pointConstraint1.w0" "_shape_spine_spine2_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_spine1_pointConstraint1.ctx" "_shape_spine_spine1.tx";
connectAttr "_shape_spine_spine1_pointConstraint1.cty" "_shape_spine_spine1.ty";
connectAttr "_shape_spine_spine1_pointConstraint1.ctz" "_shape_spine_spine1.tz";
connectAttr "_shape_spine_spine1.pim" "_shape_spine_spine1_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_spine1.rp" "_shape_spine_spine1_pointConstraint1.crp";
connectAttr "_shape_spine_spine1.rpt" "_shape_spine_spine1_pointConstraint1.crt"
		;
connectAttr "tpl_spine_chain1.t" "_shape_spine_spine1_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_spine_chain1.rp" "_shape_spine_spine1_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_spine_chain1.rpt" "_shape_spine_spine1_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_spine_chain1.pm" "_shape_spine_spine1_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_spine_spine1_pointConstraint1.w0" "_shape_spine_spine1_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_spine_mid_pointConstraint1.ctx" "_shape_spine_spine_mid.tx"
		;
connectAttr "_shape_spine_spine_mid_pointConstraint1.cty" "_shape_spine_spine_mid.ty"
		;
connectAttr "_shape_spine_spine_mid_pointConstraint1.ctz" "_shape_spine_spine_mid.tz"
		;
connectAttr "_shape_spine_spine_mid_aimConstraint1.crx" "_shape_spine_spine_mid.rx"
		;
connectAttr "_shape_spine_spine_mid_aimConstraint1.cry" "_shape_spine_spine_mid.ry"
		;
connectAttr "_shape_spine_spine_mid_aimConstraint1.crz" "_shape_spine_spine_mid.rz"
		;
connectAttr "_shape_spine_spine_mid.pim" "_shape_spine_spine_mid_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_spine_mid.rp" "_shape_spine_spine_mid_pointConstraint1.crp"
		;
connectAttr "_shape_spine_spine_mid.rpt" "_shape_spine_spine_mid_pointConstraint1.crt"
		;
connectAttr "tpl_spine_chain1.t" "_shape_spine_spine_mid_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_spine_chain1.rp" "_shape_spine_spine_mid_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_spine_chain1.rpt" "_shape_spine_spine_mid_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_spine_chain1.pm" "_shape_spine_spine_mid_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_spine_spine_mid_pointConstraint1.w0" "_shape_spine_spine_mid_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_spine_chain2.t" "_shape_spine_spine_mid_pointConstraint1.tg[1].tt"
		;
connectAttr "tpl_spine_chain2.rp" "_shape_spine_spine_mid_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_spine_chain2.rpt" "_shape_spine_spine_mid_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_spine_chain2.pm" "_shape_spine_spine_mid_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_spine_spine_mid_pointConstraint1.w1" "_shape_spine_spine_mid_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_spine_spine_mid.pim" "_shape_spine_spine_mid_aimConstraint1.cpim"
		;
connectAttr "_shape_spine_spine_mid.t" "_shape_spine_spine_mid_aimConstraint1.ct"
		;
connectAttr "_shape_spine_spine_mid.rp" "_shape_spine_spine_mid_aimConstraint1.crp"
		;
connectAttr "_shape_spine_spine_mid.rpt" "_shape_spine_spine_mid_aimConstraint1.crt"
		;
connectAttr "_shape_spine_spine_mid.ro" "_shape_spine_spine_mid_aimConstraint1.cro"
		;
connectAttr "tpl_spine_chain2.t" "_shape_spine_spine_mid_aimConstraint1.tg[0].tt"
		;
connectAttr "tpl_spine_chain2.rp" "_shape_spine_spine_mid_aimConstraint1.tg[0].trp"
		;
connectAttr "tpl_spine_chain2.rpt" "_shape_spine_spine_mid_aimConstraint1.tg[0].trt"
		;
connectAttr "tpl_spine_chain2.pm" "_shape_spine_spine_mid_aimConstraint1.tg[0].tpm"
		;
connectAttr "_shape_spine_spine_mid_aimConstraint1.w0" "_shape_spine_spine_mid_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_spine.s" "tpl_spine_hips.is";
connectAttr "_shape_leg_digits_L_pointConstraint1.ctx" "_shape_leg_digits_L.tx";
connectAttr "_shape_leg_digits_L_pointConstraint1.cty" "_shape_leg_digits_L.ty";
connectAttr "_shape_leg_digits_L_pointConstraint1.ctz" "_shape_leg_digits_L.tz";
connectAttr "_shape_leg_digits_L_aimConstraint1.crx" "_shape_leg_digits_L.rx";
connectAttr "_shape_leg_digits_L_aimConstraint1.cry" "_shape_leg_digits_L.ry";
connectAttr "_shape_leg_digits_L_aimConstraint1.crz" "_shape_leg_digits_L.rz";
connectAttr "_shape_leg_digits_L.pim" "_shape_leg_digits_L_pointConstraint1.cpim"
		;
connectAttr "_shape_leg_digits_L.rp" "_shape_leg_digits_L_pointConstraint1.crp";
connectAttr "_shape_leg_digits_L.rpt" "_shape_leg_digits_L_pointConstraint1.crt"
		;
connectAttr "tpl_leg_digits.t" "_shape_leg_digits_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_digits.rp" "_shape_leg_digits_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_leg_digits.rpt" "_shape_leg_digits_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_leg_digits.pm" "_shape_leg_digits_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_leg_digits_L_pointConstraint1.w0" "_shape_leg_digits_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_digits_L.pim" "_shape_leg_digits_L_aimConstraint1.cpim";
connectAttr "_shape_leg_digits_L.t" "_shape_leg_digits_L_aimConstraint1.ct";
connectAttr "_shape_leg_digits_L.rp" "_shape_leg_digits_L_aimConstraint1.crp";
connectAttr "_shape_leg_digits_L.rpt" "_shape_leg_digits_L_aimConstraint1.crt";
connectAttr "_shape_leg_digits_L.ro" "_shape_leg_digits_L_aimConstraint1.cro";
connectAttr "tpl_leg_tip.t" "_shape_leg_digits_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_tip.rp" "_shape_leg_digits_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_tip.rpt" "_shape_leg_digits_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_tip.pm" "_shape_leg_digits_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_digits_L_aimConstraint1.w0" "_shape_leg_digits_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg_limb3.wm" "_shape_leg_digits_L_aimConstraint1.wum";
connectAttr "tpl_leg_digits.s" "tpl_leg_bank_ext.is";
connectAttr "tpl_leg_digits.s" "tpl_leg_bank_int.is";
connectAttr "_shape_leg_ctrls_ik_offset_L_pointConstraint1.ctx" "_shape_leg_ctrls_ik_offset_L.tx"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_pointConstraint1.cty" "_shape_leg_ctrls_ik_offset_L.ty"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_pointConstraint1.ctz" "_shape_leg_ctrls_ik_offset_L.tz"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_aimConstraint1.crx" "_shape_leg_ctrls_ik_offset_L.rx"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_aimConstraint1.cry" "_shape_leg_ctrls_ik_offset_L.ry"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_aimConstraint1.crz" "_shape_leg_ctrls_ik_offset_L.rz"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.pim" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.cpim"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.rp" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.crp"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.rpt" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.crt"
		;
connectAttr "tpl_leg_digits.t" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_leg_digits.rp" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_leg_digits.rpt" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_leg_digits.pm" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_pointConstraint1.w0" "_shape_leg_ctrls_ik_offset_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.pim" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.cpim"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.t" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.ct"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.rp" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.crp"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.rpt" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.crt"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L.ro" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.cro"
		;
connectAttr "tpl_leg_limb3.t" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.tg[0].tt"
		;
connectAttr "tpl_leg_limb3.rp" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.tg[0].trp"
		;
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.tg[0].trt"
		;
connectAttr "tpl_leg_limb3.pm" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.tg[0].tpm"
		;
connectAttr "_shape_leg_ctrls_ik_offset_L_aimConstraint1.w0" "_shape_leg_ctrls_ik_offset_L_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_limb3_L_pointConstraint1.ctx" "_shape_leg_limb3_L.tx";
connectAttr "_shape_leg_limb3_L_pointConstraint1.cty" "_shape_leg_limb3_L.ty";
connectAttr "_shape_leg_limb3_L_pointConstraint1.ctz" "_shape_leg_limb3_L.tz";
connectAttr "aimConstraint107.crx" "_shape_leg_limb3_L.rx";
connectAttr "aimConstraint107.cry" "_shape_leg_limb3_L.ry";
connectAttr "aimConstraint107.crz" "_shape_leg_limb3_L.rz";
connectAttr "_shape_leg_limb3_L.pim" "_shape_leg_limb3_L_pointConstraint1.cpim";
connectAttr "_shape_leg_limb3_L.rp" "_shape_leg_limb3_L_pointConstraint1.crp";
connectAttr "_shape_leg_limb3_L.rpt" "_shape_leg_limb3_L_pointConstraint1.crt";
connectAttr "tpl_leg_limb3.t" "_shape_leg_limb3_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_limb3_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_limb3_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_limb3_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_limb3_L_pointConstraint1.w0" "_shape_leg_limb3_L_pointConstraint1.tg[0].tw"
		;
connectAttr "pointConstraint107.ct" "aimConstraint107.tg[0].tt";
connectAttr "_shape_leg_limb3_L.pim" "aimConstraint107.cpim";
connectAttr "tpl_leg_tip.wm" "aimConstraint107.wum";
connectAttr "tpl_leg_limb3.t" "pointConstraint107.tg[0].tt";
connectAttr "tpl_leg_limb3.pm" "pointConstraint107.tg[0].tpm";
connectAttr "_shape_leg_ik_L_pointConstraint1.ctx" "_shape_leg_ik_L.tx";
connectAttr "_shape_leg_ik_L_pointConstraint1.cty" "_shape_leg_ik_L.ty";
connectAttr "_shape_leg_ik_L_pointConstraint1.ctz" "_shape_leg_ik_L.tz";
connectAttr "aimConstraint108.crx" "_shape_leg_ik_L.rx";
connectAttr "aimConstraint108.cry" "_shape_leg_ik_L.ry";
connectAttr "aimConstraint108.crz" "_shape_leg_ik_L.rz";
connectAttr "_shape_leg_ik_L.pim" "_shape_leg_ik_L_pointConstraint1.cpim";
connectAttr "_shape_leg_ik_L.rp" "_shape_leg_ik_L_pointConstraint1.crp";
connectAttr "_shape_leg_ik_L.rpt" "_shape_leg_ik_L_pointConstraint1.crt";
connectAttr "tpl_leg_limb3.t" "_shape_leg_ik_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_ik_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_ik_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_ik_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_ik_L_pointConstraint1.w0" "_shape_leg_ik_L_pointConstraint1.tg[0].tw"
		;
connectAttr "pointConstraint108.ct" "aimConstraint108.tg[0].tt";
connectAttr "_shape_leg_ik_L.pim" "aimConstraint108.cpim";
connectAttr "tpl_leg_tip.wm" "aimConstraint108.wum";
connectAttr "tpl_leg_limb3.t" "pointConstraint108.tg[0].tt";
connectAttr "tpl_leg_limb3.pm" "pointConstraint108.tg[0].tpm";
connectAttr "_shape_leg_limb2_L_pointConstraint1.ctx" "_shape_leg_limb2_L.tx";
connectAttr "_shape_leg_limb2_L_pointConstraint1.cty" "_shape_leg_limb2_L.ty";
connectAttr "_shape_leg_limb2_L_pointConstraint1.ctz" "_shape_leg_limb2_L.tz";
connectAttr "_shape_leg_limb2_L_aimConstraint1.crx" "_shape_leg_limb2_L.rx";
connectAttr "_shape_leg_limb2_L_aimConstraint1.cry" "_shape_leg_limb2_L.ry";
connectAttr "_shape_leg_limb2_L_aimConstraint1.crz" "_shape_leg_limb2_L.rz";
connectAttr "_shape_leg_limb2_L.pim" "_shape_leg_limb2_L_pointConstraint1.cpim";
connectAttr "_shape_leg_limb2_L.rp" "_shape_leg_limb2_L_pointConstraint1.crp";
connectAttr "_shape_leg_limb2_L.rpt" "_shape_leg_limb2_L_pointConstraint1.crt";
connectAttr "tpl_leg_limb2.t" "_shape_leg_limb2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_limb2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_limb2_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_limb2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_limb2_L_pointConstraint1.w0" "_shape_leg_limb2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_limb2_L.pim" "_shape_leg_limb2_L_aimConstraint1.cpim";
connectAttr "_shape_leg_limb2_L.t" "_shape_leg_limb2_L_aimConstraint1.ct";
connectAttr "_shape_leg_limb2_L.rp" "_shape_leg_limb2_L_aimConstraint1.crp";
connectAttr "_shape_leg_limb2_L.rpt" "_shape_leg_limb2_L_aimConstraint1.crt";
connectAttr "_shape_leg_limb2_L.ro" "_shape_leg_limb2_L_aimConstraint1.cro";
connectAttr "tpl_leg_limb3.t" "_shape_leg_limb2_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_limb2_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_limb2_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_limb2_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_limb2_L_aimConstraint1.w0" "_shape_leg_limb2_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg.wm" "_shape_leg_limb2_L_aimConstraint1.wum";
connectAttr "_shape_leg_bend2_L_pointConstraint1.ctx" "_shape_leg_bend2_L.tx";
connectAttr "_shape_leg_bend2_L_pointConstraint1.cty" "_shape_leg_bend2_L.ty";
connectAttr "_shape_leg_bend2_L_pointConstraint1.ctz" "_shape_leg_bend2_L.tz";
connectAttr "_shape_leg_bend2_L_aimConstraint1.crx" "_shape_leg_bend2_L.rx";
connectAttr "_shape_leg_bend2_L_aimConstraint1.cry" "_shape_leg_bend2_L.ry";
connectAttr "_shape_leg_bend2_L_aimConstraint1.crz" "_shape_leg_bend2_L.rz";
connectAttr "_shape_leg_bend2_L.pim" "_shape_leg_bend2_L_pointConstraint1.cpim";
connectAttr "_shape_leg_bend2_L.rp" "_shape_leg_bend2_L_pointConstraint1.crp";
connectAttr "_shape_leg_bend2_L.rpt" "_shape_leg_bend2_L_pointConstraint1.crt";
connectAttr "tpl_leg_limb2.t" "_shape_leg_bend2_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_bend2_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_bend2_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_bend2_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_bend2_L_pointConstraint1.w0" "_shape_leg_bend2_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg_limb3.t" "_shape_leg_bend2_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_bend2_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_bend2_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_bend2_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_leg_bend2_L_pointConstraint1.w1" "_shape_leg_bend2_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_leg_bend2_L.pim" "_shape_leg_bend2_L_aimConstraint1.cpim";
connectAttr "_shape_leg_bend2_L.t" "_shape_leg_bend2_L_aimConstraint1.ct";
connectAttr "_shape_leg_bend2_L.rp" "_shape_leg_bend2_L_aimConstraint1.crp";
connectAttr "_shape_leg_bend2_L.rpt" "_shape_leg_bend2_L_aimConstraint1.crt";
connectAttr "_shape_leg_bend2_L.ro" "_shape_leg_bend2_L_aimConstraint1.cro";
connectAttr "tpl_leg_limb3.t" "_shape_leg_bend2_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_bend2_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_bend2_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_bend2_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_bend2_L_aimConstraint1.w0" "_shape_leg_bend2_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg.wm" "_shape_leg_bend2_L_aimConstraint1.wum";
connectAttr "_shape_leg_tweak_L_pointConstraint1.ctx" "_shape_leg_tweak_L.tx";
connectAttr "_shape_leg_tweak_L_pointConstraint1.cty" "_shape_leg_tweak_L.ty";
connectAttr "_shape_leg_tweak_L_pointConstraint1.ctz" "_shape_leg_tweak_L.tz";
connectAttr "_shape_leg_tweak_L_aimConstraint1.crx" "_shape_leg_tweak_L.rx";
connectAttr "_shape_leg_tweak_L_aimConstraint1.cry" "_shape_leg_tweak_L.ry";
connectAttr "_shape_leg_tweak_L_aimConstraint1.crz" "_shape_leg_tweak_L.rz";
connectAttr "_shape_leg_tweak_L.pim" "_shape_leg_tweak_L_pointConstraint1.cpim";
connectAttr "_shape_leg_tweak_L.rp" "_shape_leg_tweak_L_pointConstraint1.crp";
connectAttr "_shape_leg_tweak_L.rpt" "_shape_leg_tweak_L_pointConstraint1.crt";
connectAttr "tpl_leg_limb2.t" "_shape_leg_tweak_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_tweak_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_tweak_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_tweak_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_tweak_L_pointConstraint1.w0" "_shape_leg_tweak_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_tweak_L.pim" "_shape_leg_tweak_L_aimConstraint1.cpim";
connectAttr "_shape_leg_tweak_L.t" "_shape_leg_tweak_L_aimConstraint1.ct";
connectAttr "_shape_leg_tweak_L.rp" "_shape_leg_tweak_L_aimConstraint1.crp";
connectAttr "_shape_leg_tweak_L.rpt" "_shape_leg_tweak_L_aimConstraint1.crt";
connectAttr "_shape_leg_tweak_L.ro" "_shape_leg_tweak_L_aimConstraint1.cro";
connectAttr "tpl_leg_limb3.t" "_shape_leg_tweak_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb3.rp" "_shape_leg_tweak_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb3.rpt" "_shape_leg_tweak_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb3.pm" "_shape_leg_tweak_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_tweak_L_aimConstraint1.w0" "_shape_leg_tweak_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg.wm" "_shape_leg_tweak_L_aimConstraint1.wum";
connectAttr "_shape_leg_ctrls_clavicle_L_pointConstraint1.ctx" "_shape_leg_ctrls_clavicle_L.tx"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_pointConstraint1.cty" "_shape_leg_ctrls_clavicle_L.ty"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_pointConstraint1.ctz" "_shape_leg_ctrls_clavicle_L.tz"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_aimConstraint1.crx" "_shape_leg_ctrls_clavicle_L.rx"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_aimConstraint1.cry" "_shape_leg_ctrls_clavicle_L.ry"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_aimConstraint1.crz" "_shape_leg_ctrls_clavicle_L.rz"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.pim" "_shape_leg_ctrls_clavicle_L_pointConstraint1.cpim"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.rp" "_shape_leg_ctrls_clavicle_L_pointConstraint1.crp"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.rpt" "_shape_leg_ctrls_clavicle_L_pointConstraint1.crt"
		;
connectAttr "tpl_leg_clav.t" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[0].tt"
		;
connectAttr "tpl_leg_clav.rp" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[0].trp"
		;
connectAttr "tpl_leg_clav.rpt" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[0].trt"
		;
connectAttr "tpl_leg_clav.pm" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[0].tpm"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_pointConstraint1.w0" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg.t" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_leg.rp" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[1].trp"
		;
connectAttr "tpl_leg.rpt" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[1].trt"
		;
connectAttr "tpl_leg.pm" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[1].tpm"
		;
connectAttr "_shape_leg_ctrls_clavicle_L_pointConstraint1.w1" "_shape_leg_ctrls_clavicle_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.pim" "_shape_leg_ctrls_clavicle_L_aimConstraint1.cpim"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.t" "_shape_leg_ctrls_clavicle_L_aimConstraint1.ct"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.rp" "_shape_leg_ctrls_clavicle_L_aimConstraint1.crp"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.rpt" "_shape_leg_ctrls_clavicle_L_aimConstraint1.crt"
		;
connectAttr "_shape_leg_ctrls_clavicle_L.ro" "_shape_leg_ctrls_clavicle_L_aimConstraint1.cro"
		;
connectAttr "tpl_leg.t" "_shape_leg_ctrls_clavicle_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg.rp" "_shape_leg_ctrls_clavicle_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg.rpt" "_shape_leg_ctrls_clavicle_L_aimConstraint1.tg[0].trt"
		;
connectAttr "tpl_leg.pm" "_shape_leg_ctrls_clavicle_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_ctrls_clavicle_L_aimConstraint1.w0" "_shape_leg_ctrls_clavicle_L_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_limb1_L_pointConstraint1.ctx" "_shape_leg_limb1_L.tx";
connectAttr "_shape_leg_limb1_L_pointConstraint1.cty" "_shape_leg_limb1_L.ty";
connectAttr "_shape_leg_limb1_L_pointConstraint1.ctz" "_shape_leg_limb1_L.tz";
connectAttr "_shape_leg_limb1_L_aimConstraint1.crx" "_shape_leg_limb1_L.rx";
connectAttr "_shape_leg_limb1_L_aimConstraint1.cry" "_shape_leg_limb1_L.ry";
connectAttr "_shape_leg_limb1_L_aimConstraint1.crz" "_shape_leg_limb1_L.rz";
connectAttr "_shape_leg_limb1_L.pim" "_shape_leg_limb1_L_pointConstraint1.cpim";
connectAttr "_shape_leg_limb1_L.rp" "_shape_leg_limb1_L_pointConstraint1.crp";
connectAttr "_shape_leg_limb1_L.rpt" "_shape_leg_limb1_L_pointConstraint1.crt";
connectAttr "tpl_leg.t" "_shape_leg_limb1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg.rp" "_shape_leg_limb1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg.rpt" "_shape_leg_limb1_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg.pm" "_shape_leg_limb1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_limb1_L_pointConstraint1.w0" "_shape_leg_limb1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_leg_limb1_L.pim" "_shape_leg_limb1_L_aimConstraint1.cpim";
connectAttr "_shape_leg_limb1_L.t" "_shape_leg_limb1_L_aimConstraint1.ct";
connectAttr "_shape_leg_limb1_L.rp" "_shape_leg_limb1_L_aimConstraint1.crp";
connectAttr "_shape_leg_limb1_L.rpt" "_shape_leg_limb1_L_aimConstraint1.crt";
connectAttr "_shape_leg_limb1_L.ro" "_shape_leg_limb1_L_aimConstraint1.cro";
connectAttr "tpl_leg_limb2.t" "_shape_leg_limb1_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_limb1_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_limb1_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_limb1_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_limb1_L_aimConstraint1.w0" "_shape_leg_limb1_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg_limb3.wm" "_shape_leg_limb1_L_aimConstraint1.wum";
connectAttr "_shape_leg_bend1_L_pointConstraint1.ctx" "_shape_leg_bend1_L.tx";
connectAttr "_shape_leg_bend1_L_pointConstraint1.cty" "_shape_leg_bend1_L.ty";
connectAttr "_shape_leg_bend1_L_pointConstraint1.ctz" "_shape_leg_bend1_L.tz";
connectAttr "_shape_leg_bend1_L_aimConstraint1.crx" "_shape_leg_bend1_L.rx";
connectAttr "_shape_leg_bend1_L_aimConstraint1.cry" "_shape_leg_bend1_L.ry";
connectAttr "_shape_leg_bend1_L_aimConstraint1.crz" "_shape_leg_bend1_L.rz";
connectAttr "_shape_leg_bend1_L.pim" "_shape_leg_bend1_L_pointConstraint1.cpim";
connectAttr "_shape_leg_bend1_L.rp" "_shape_leg_bend1_L_pointConstraint1.crp";
connectAttr "_shape_leg_bend1_L.rpt" "_shape_leg_bend1_L_pointConstraint1.crt";
connectAttr "tpl_leg.t" "_shape_leg_bend1_L_pointConstraint1.tg[0].tt";
connectAttr "tpl_leg.rp" "_shape_leg_bend1_L_pointConstraint1.tg[0].trp";
connectAttr "tpl_leg.rpt" "_shape_leg_bend1_L_pointConstraint1.tg[0].trt";
connectAttr "tpl_leg.pm" "_shape_leg_bend1_L_pointConstraint1.tg[0].tpm";
connectAttr "_shape_leg_bend1_L_pointConstraint1.w0" "_shape_leg_bend1_L_pointConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg_limb2.t" "_shape_leg_bend1_L_pointConstraint1.tg[1].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_bend1_L_pointConstraint1.tg[1].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_bend1_L_pointConstraint1.tg[1].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_bend1_L_pointConstraint1.tg[1].tpm";
connectAttr "_shape_leg_bend1_L_pointConstraint1.w1" "_shape_leg_bend1_L_pointConstraint1.tg[1].tw"
		;
connectAttr "_shape_leg_bend1_L.pim" "_shape_leg_bend1_L_aimConstraint1.cpim";
connectAttr "_shape_leg_bend1_L.t" "_shape_leg_bend1_L_aimConstraint1.ct";
connectAttr "_shape_leg_bend1_L.rp" "_shape_leg_bend1_L_aimConstraint1.crp";
connectAttr "_shape_leg_bend1_L.rpt" "_shape_leg_bend1_L_aimConstraint1.crt";
connectAttr "_shape_leg_bend1_L.ro" "_shape_leg_bend1_L_aimConstraint1.cro";
connectAttr "tpl_leg_limb2.t" "_shape_leg_bend1_L_aimConstraint1.tg[0].tt";
connectAttr "tpl_leg_limb2.rp" "_shape_leg_bend1_L_aimConstraint1.tg[0].trp";
connectAttr "tpl_leg_limb2.rpt" "_shape_leg_bend1_L_aimConstraint1.tg[0].trt";
connectAttr "tpl_leg_limb2.pm" "_shape_leg_bend1_L_aimConstraint1.tg[0].tpm";
connectAttr "_shape_leg_bend1_L_aimConstraint1.w0" "_shape_leg_bend1_L_aimConstraint1.tg[0].tw"
		;
connectAttr "tpl_leg_limb3.wm" "_shape_leg_bend1_L_aimConstraint1.wum";
connectAttr "_shape_spine_cog_pointConstraint1.ctx" "_shape_spine_cog.tx";
connectAttr "_shape_spine_cog_pointConstraint1.cty" "_shape_spine_cog.ty";
connectAttr "_shape_spine_cog_pointConstraint1.ctz" "_shape_spine_cog.tz";
connectAttr "_shape_spine_cog.pim" "_shape_spine_cog_pointConstraint1.cpim";
connectAttr "_shape_spine_cog.rp" "_shape_spine_cog_pointConstraint1.crp";
connectAttr "_shape_spine_cog.rpt" "_shape_spine_cog_pointConstraint1.crt";
connectAttr "tpl_spine.t" "_shape_spine_cog_pointConstraint1.tg[0].tt";
connectAttr "tpl_spine.rp" "_shape_spine_cog_pointConstraint1.tg[0].trp";
connectAttr "tpl_spine.rpt" "_shape_spine_cog_pointConstraint1.tg[0].trt";
connectAttr "tpl_spine.pm" "_shape_spine_cog_pointConstraint1.tg[0].tpm";
connectAttr "_shape_spine_cog_pointConstraint1.w0" "_shape_spine_cog_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_pelvis_pointConstraint1.ctx" "_shape_spine_pelvis.tx";
connectAttr "_shape_spine_pelvis_pointConstraint1.cty" "_shape_spine_pelvis.ty";
connectAttr "_shape_spine_pelvis_pointConstraint1.ctz" "_shape_spine_pelvis.tz";
connectAttr "_shape_spine_pelvis_aimConstraint1.crx" "_shape_spine_pelvis.rx";
connectAttr "_shape_spine_pelvis_aimConstraint1.cry" "_shape_spine_pelvis.ry";
connectAttr "_shape_spine_pelvis_aimConstraint1.crz" "_shape_spine_pelvis.rz";
connectAttr "_shape_spine_pelvis.pim" "_shape_spine_pelvis_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_pelvis.rp" "_shape_spine_pelvis_pointConstraint1.crp";
connectAttr "_shape_spine_pelvis.rpt" "_shape_spine_pelvis_pointConstraint1.crt"
		;
connectAttr "tpl_spine.t" "_shape_spine_pelvis_pointConstraint1.tg[0].tt";
connectAttr "tpl_spine.rp" "_shape_spine_pelvis_pointConstraint1.tg[0].trp";
connectAttr "tpl_spine.rpt" "_shape_spine_pelvis_pointConstraint1.tg[0].trt";
connectAttr "tpl_spine.pm" "_shape_spine_pelvis_pointConstraint1.tg[0].tpm";
connectAttr "_shape_spine_pelvis_pointConstraint1.w0" "_shape_spine_pelvis_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_pelvis.pim" "_shape_spine_pelvis_aimConstraint1.cpim";
connectAttr "_shape_spine_pelvis.t" "_shape_spine_pelvis_aimConstraint1.ct";
connectAttr "_shape_spine_pelvis.rp" "_shape_spine_pelvis_aimConstraint1.crp";
connectAttr "_shape_spine_pelvis.rpt" "_shape_spine_pelvis_aimConstraint1.crt";
connectAttr "_shape_spine_pelvis.ro" "_shape_spine_pelvis_aimConstraint1.cro";
connectAttr "tpl_spine_hips.t" "_shape_spine_pelvis_aimConstraint1.tg[0].tt";
connectAttr "tpl_spine_hips.rp" "_shape_spine_pelvis_aimConstraint1.tg[0].trp";
connectAttr "tpl_spine_hips.rpt" "_shape_spine_pelvis_aimConstraint1.tg[0].trt";
connectAttr "tpl_spine_hips.pm" "_shape_spine_pelvis_aimConstraint1.tg[0].tpm";
connectAttr "_shape_spine_pelvis_aimConstraint1.w0" "_shape_spine_pelvis_aimConstraint1.tg[0].tw"
		;
connectAttr "_shape_spine_pelvisIK_pointConstraint1.ctx" "_shape_spine_pelvisIK.tx"
		;
connectAttr "_shape_spine_pelvisIK_pointConstraint1.cty" "_shape_spine_pelvisIK.ty"
		;
connectAttr "_shape_spine_pelvisIK_pointConstraint1.ctz" "_shape_spine_pelvisIK.tz"
		;
connectAttr "aimConstraint105.crx" "_shape_spine_pelvisIK.rx";
connectAttr "aimConstraint105.cry" "_shape_spine_pelvisIK.ry";
connectAttr "aimConstraint105.crz" "_shape_spine_pelvisIK.rz";
connectAttr "_shape_spine_pelvisIK.pim" "_shape_spine_pelvisIK_pointConstraint1.cpim"
		;
connectAttr "_shape_spine_pelvisIK.rp" "_shape_spine_pelvisIK_pointConstraint1.crp"
		;
connectAttr "_shape_spine_pelvisIK.rpt" "_shape_spine_pelvisIK_pointConstraint1.crt"
		;
connectAttr "tpl_spine.t" "_shape_spine_pelvisIK_pointConstraint1.tg[0].tt";
connectAttr "tpl_spine.rp" "_shape_spine_pelvisIK_pointConstraint1.tg[0].trp";
connectAttr "tpl_spine.rpt" "_shape_spine_pelvisIK_pointConstraint1.tg[0].trt";
connectAttr "tpl_spine.pm" "_shape_spine_pelvisIK_pointConstraint1.tg[0].tpm";
connectAttr "_shape_spine_pelvisIK_pointConstraint1.w0" "_shape_spine_pelvisIK_pointConstraint1.tg[0].tw"
		;
connectAttr "pointConstraint105.ct" "aimConstraint105.tg[0].tt";
connectAttr "_shape_spine_pelvisIK.pim" "aimConstraint105.cpim";
connectAttr "tpl_spine.t" "pointConstraint105.tg[0].tt";
connectAttr "tpl_spine.pm" "pointConstraint105.tg[0].tpm";
connectAttr "_shape_world_fly_pointConstraint1.ctx" "_shape_world_fly.tx";
connectAttr "_shape_world_fly_pointConstraint1.cty" "_shape_world_fly.ty";
connectAttr "_shape_world_fly_pointConstraint1.ctz" "_shape_world_fly.tz";
connectAttr "_shape_world_fly.pim" "_shape_world_fly_pointConstraint1.cpim";
connectAttr "_shape_world_fly.rp" "_shape_world_fly_pointConstraint1.crp";
connectAttr "_shape_world_fly.rpt" "_shape_world_fly_pointConstraint1.crt";
connectAttr "tpl_world_root.t" "_shape_world_fly_pointConstraint1.tg[0].tt";
connectAttr "tpl_world_root.rp" "_shape_world_fly_pointConstraint1.tg[0].trp";
connectAttr "tpl_world_root.rpt" "_shape_world_fly_pointConstraint1.tg[0].trt";
connectAttr "tpl_world_root.pm" "_shape_world_fly_pointConstraint1.tg[0].tpm";
connectAttr "_shape_world_fly_pointConstraint1.w0" "_shape_world_fly_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_world_world_pointConstraint1.ctx" "_shape_world_world.tx";
connectAttr "_shape_world_world_pointConstraint1.cty" "_shape_world_world.ty";
connectAttr "_shape_world_world_pointConstraint1.ctz" "_shape_world_world.tz";
connectAttr "_shape_world_world.pim" "_shape_world_world_pointConstraint1.cpim";
connectAttr "_shape_world_world.rp" "_shape_world_world_pointConstraint1.crp";
connectAttr "_shape_world_world.rpt" "_shape_world_world_pointConstraint1.crt";
connectAttr "tpl_world.t" "_shape_world_world_pointConstraint1.tg[0].tt";
connectAttr "tpl_world.rp" "_shape_world_world_pointConstraint1.tg[0].trp";
connectAttr "tpl_world.rpt" "_shape_world_world_pointConstraint1.tg[0].trt";
connectAttr "tpl_world.pm" "_shape_world_world_pointConstraint1.tg[0].tpm";
connectAttr "_shape_world_world_pointConstraint1.w0" "_shape_world_world_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_world_move_pointConstraint1.ctx" "_shape_world_move.tx";
connectAttr "_shape_world_move_pointConstraint1.cty" "_shape_world_move.ty";
connectAttr "_shape_world_move_pointConstraint1.ctz" "_shape_world_move.tz";
connectAttr "_shape_world_move.pim" "_shape_world_move_pointConstraint1.cpim";
connectAttr "_shape_world_move.rp" "_shape_world_move_pointConstraint1.crp";
connectAttr "_shape_world_move.rpt" "_shape_world_move_pointConstraint1.crt";
connectAttr "tpl_world.t" "_shape_world_move_pointConstraint1.tg[0].tt";
connectAttr "tpl_world.rp" "_shape_world_move_pointConstraint1.tg[0].trp";
connectAttr "tpl_world.rpt" "_shape_world_move_pointConstraint1.tg[0].trt";
connectAttr "tpl_world.pm" "_shape_world_move_pointConstraint1.tg[0].tpm";
connectAttr "_shape_world_move_pointConstraint1.w0" "_shape_world_move_pointConstraint1.tg[0].tw"
		;
connectAttr "_shape_world_scale_pointConstraint1.ctx" "_shape_world_scale.tx";
connectAttr "_shape_world_scale_pointConstraint1.cty" "_shape_world_scale.ty";
connectAttr "_shape_world_scale_pointConstraint1.ctz" "_shape_world_scale.tz";
connectAttr "_shape_world_scale.pim" "_shape_world_scale_pointConstraint1.cpim";
connectAttr "_shape_world_scale.rp" "_shape_world_scale_pointConstraint1.crp";
connectAttr "_shape_world_scale.rpt" "_shape_world_scale_pointConstraint1.crt";
connectAttr "tpl_world.t" "_shape_world_scale_pointConstraint1.tg[0].tt";
connectAttr "tpl_world.rp" "_shape_world_scale_pointConstraint1.tg[0].trp";
connectAttr "tpl_world.rpt" "_shape_world_scale_pointConstraint1.tg[0].trt";
connectAttr "tpl_world.pm" "_shape_world_scale_pointConstraint1.tg[0].tpm";
connectAttr "_shape_world_scale_pointConstraint1.w0" "_shape_world_scale_pointConstraint1.tg[0].tw"
		;
// End of tpl_biped.ma
