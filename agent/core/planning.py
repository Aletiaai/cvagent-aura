# Purpose: Decide the sequence of actions for the agent. Initially, this might be simple.
def plan_resume_processing(source_type: str, options: dict):
    """Determines the steps needed based on the source and options."""
    plan = []
    if source_type == "file":
        plan.append({"action": "extract_info", "params": {"file_path": options["file_path"]}})
    elif source_type == "drive":
        plan.append({"action": "list_drive_files", "params": {"folder_path": options["folder_path"]}})
        # The execution step will loop through files based on this plan item
        plan.append({"action": "process_drive_file_loop", "params": {}}) 
    
    # Common steps after initial processing/extraction
    if options.get("analyze", False): # Example option
         plan.append({"action": "analyze_resume", "params": {}}) # Params might include candidate_id
    if options.get("ask_questions", False): # Example option
         plan.append({"action": "generate_questions", "params": {}})
    if options.get("send_email", False): # Example option
        plan.append({"action": "format_email", "params": {}}) # Could be feedback or questions email
        plan.append({"action": "send_email_draft", "params": {}})
        
    return plan 

# Note: This is highly conceptual. Your execution.py will interpret this plan. You might start without a separate planning.py and embed this logic directly in execution.py, but separating it is good for agent design.