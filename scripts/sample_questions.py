"""The sample form's questions, written by hand for the first build.

This stands in for Gemini's conversion of samples/pt-intake/original.pdf until a
GEMINI_API_KEY is available. It uses exactly the converter's output format, so
the patient flow can be built and tested with no AI. Once the key is in, slice 5
converts the PDF live and replaces samples/pt-intake/form.json with Gemini's output.

    python scripts/sample_questions.py  ->  samples/pt-intake/form.json
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "samples" / "pt-intake" / "form.json"

S = {
    "you": ("About you", "तपाईंको बारेमा"),
    "emergency": ("Emergency contact", "आपतकालीन सम्पर्क"),
    "accident": ("The accident", "दुर्घटना"),
    "care": ("Care so far", "अहिलेसम्मको उपचार"),
    "claims": ("Claims", "क्लेम र वकिल"),
    "insurance": ("Health insurance", "स्वास्थ्य बीमा"),
    "accident_claim": ("Accident claim", "दुर्घटनाको बीमा क्लेम"),
    "pain": ("Your pain", "तपाईंको दुखाइ"),
    "history": ("Medical history", "स्वास्थ्यको इतिहास"),
    "signature": ("Signature", "हस्ताक्षर"),
}

YES_NO = [{"value": "Yes", "en": "Yes", "ne": "हो"}, {"value": "No", "en": "No", "ne": "होइन"}]
RELATIONS = [
    {"en": "Son", "ne": "छोरा"}, {"en": "Daughter", "ne": "छोरी"}, {"en": "Husband", "ne": "श्रीमान्"},
    {"en": "Wife", "ne": "श्रीमती"}, {"en": "Brother", "ne": "दाजु / भाइ"}, {"en": "Sister", "ne": "दिदी / बहिनी"},
]


def q(id, kind, fields, en, ne, section, **extra):
    sec_en, sec_ne = S[section]
    item = {"id": id, "kind": kind, "fields": fields if isinstance(fields, list) else [fields],
            "en": en, "ne": ne, "section_en": sec_en, "section_ne": sec_ne}
    item.update(extra)
    return item


QUESTIONS = [
    q("last_name", "name", "last_name", "What is your last name (family name)?", "तपाईंको थर के हो?", "you",
      help_ne="जस्तै: न्यौपाने, गुरुङ, श्रेष्ठ"),
    q("first_name", "name", "first_name", "What is your first name?", "तपाईंको नाम के हो? (थर बाहेक)", "you"),
    q("middle_initial", "name", "middle_initial", "What is the first letter of your middle name, if you have one?",
      "तपाईंको बीचको नाम छ भने, त्यसको पहिलो अक्षर के हो?", "you", optional=True,
      help_ne="छैन भने ‘थाहा छैन / पछि दिन्छु’ थिच्नुहोस्।"),
    q("date_of_birth", "date", "date_of_birth", "What is your date of birth?", "तपाईंको जन्म मिति कहिले हो?", "you",
      format="MM/DD/YYYY", help_ne="नेपाली वा अंग्रेजी, जुन पात्रोमा याद छ, त्यही भन्नुहोस्।"),
    q("phone", "number", "phone", "What is your phone number?", "तपाईंको फोन नम्बर के हो?", "you"),
    q("preferred_language", "text", "preferred_language", "Which language do you prefer to speak?",
      "तपाईं कुन भाषामा कुरा गर्न रुचाउनुहुन्छ?", "you",
      suggestions=[{"en": "Nepali", "ne": "नेपाली"}, {"en": "Nepali and Hindi", "ne": "नेपाली र हिन्दी"}]),
    q("sex", "choice", "sex", "What is your sex?", "तपाईंको लिङ्ग के हो?", "you", options=[
        {"value": "Male", "en": "Male", "ne": "पुरुष"}, {"value": "Female", "en": "Female", "ne": "महिला"},
        {"value": "Undisclosed", "en": "Prefer not to say", "ne": "भन्न चाहन्न"}]),
    q("address_street", "text", "address_street", "What is your street address?",
      "तपाईंको घरको ठेगाना के हो? घर नम्बर र सडकको नाम भन्नुहोस्।", "you",
      help_ne="अपार्टमेन्ट भए त्यसको नम्बर पनि भन्नुहोस्।"),
    q("address_city", "text", "address_city", "Which city do you live in?", "तपाईं कुन सहरमा बस्नुहुन्छ?", "you",
      suggestions=[{"en": "Aurora", "ne": "अरोरा"}, {"en": "Denver", "ne": "डेनभर"}]),
    q("address_state", "text", "address_state", "Which state do you live in?", "कुन राज्यमा?", "you",
      suggestions=[{"en": "CO", "ne": "कोलोराडो"}]),
    q("address_zip", "number", "address_zip", "What is your ZIP code?", "तपाईंको जिप कोड (ZIP) के हो?", "you",
      help_ne="ठेगानाको अन्त्यमा हुने ५ अंकको नम्बर।"),
    q("email", "email", "email", "What is your email address?", "तपाईंको इमेल ठेगाना के हो?", "you", optional=True,
      help_ne="इमेल छैन भने ‘थाहा छैन / पछि दिन्छु’ थिच्नुहोस्।"),
    q("occupation", "text", "occupation", "What is your job?", "तपाईं के काम गर्नुहुन्छ?", "you",
      suggestions=[{"en": "Homemaker", "ne": "गृहिणी"}, {"en": "Retired", "ne": "अवकाश प्राप्त"}]),
    q("needs_interpreter", "yesno", "needs_interpreter", "Do you need an interpreter for your visits?",
      "जाँच गराउन आउँदा तपाईंलाई दोभाषे चाहिन्छ?", "you", options=YES_NO),
    q("emergency_name", "name", "emergency_name", "Who should we contact in an emergency? Their full name.",
      "आपत् परेमा कसलाई खबर गर्ने? उहाँको पूरा नाम भन्नुहोस्।", "emergency"),
    q("emergency_relationship", "text", "emergency_relationship", "How is this person related to you?",
      "उहाँ तपाईंको को हुनुहुन्छ?", "emergency", suggestions=RELATIONS),
    q("emergency_phone", "number", "emergency_phone", "What is their phone number?", "उहाँको फोन नम्बर के हो?",
      "emergency"),
    q("injury_date", "date", "injury_date", "On what date did the injury happen?", "चोट कुन दिन लाग्यो?", "accident",
      format="MM/DD/YYYY"),
    q("injury_time", "text", "injury_time", "About what time of day did it happen?", "कति बजेतिर भएको थियो?",
      "accident", suggestions=[{"en": "Morning", "ne": "बिहान"}, {"en": "Afternoon", "ne": "दिउँसो"},
                               {"en": "Evening", "ne": "बेलुका"}, {"en": "Night", "ne": "राति"}]),
    q("injury_city", "text", "injury_city", "In which city did it happen?", "कुन सहरमा भएको थियो?", "accident"),
    q("accident_type", "choice", "accident_type", "What kind of accident was it?", "कस्तो किसिमको दुर्घटना थियो?",
      "accident", options=[
          {"value": "MotorVehicle", "en": "Motor vehicle", "ne": "गाडी दुर्घटना"},
          {"value": "Work", "en": "At work", "ne": "काम गर्दा"},
          {"value": "Fall", "en": "Slip or fall", "ne": "चिप्लिएर वा लडेर"},
          {"value": "Sports", "en": "Sports", "ne": "खेल्दा"},
          {"value": "Other", "en": "Other", "ne": "अरू"}]),
    q("injury_description", "text", "injury_description", "In your own words, how did the injury happen?",
      "चोट कसरी लाग्यो? आफ्नै शब्दमा भन्नुहोस्।", "accident", long=True),
    q("seen_er", "yesno", "seen_er", "Did you go to an emergency room or urgent care?",
      "यो चोटपछि तपाईं इमर्जेन्सी वा अर्जेन्ट केयरमा जानुभयो?", "care", options=YES_NO),
    q("seen_other_doctor", "yesno", "seen_other_doctor", "Have you seen another doctor for this injury?",
      "यो चोटको लागि अरू कुनै डाक्टरलाई देखाउनुभयो?", "care", options=YES_NO),
    q("referring_doctor", "name", "referring_doctor", "What is the name of the doctor who sent you here?",
      "तपाईंलाई यहाँ पठाउने डाक्टरको नाम के हो?", "care", optional=True),
    q("referring_doctor_phone", "number", "referring_doctor_phone", "What is that doctor's phone number?",
      "ती डाक्टरको फोन नम्बर के हो?", "care", optional=True),
    q("had_imaging", "yesno", "had_imaging", "Have you had an X-ray, MRI, or CT scan for this injury?",
      "यो चोटको लागि एक्स-रे, एमआरआई वा सिटी स्क्यान गर्नुभयो?", "care", options=YES_NO),
    q("workers_comp", "yesno", "workers_comp", "Is this injury related to your job (workers' compensation)?",
      "यो चोट तपाईंको कामसँग सम्बन्धित छ? (वर्कर्स कम्पेन्सेसन)", "claims", options=YES_NO),
    q("has_attorney", "yesno", "has_attorney", "Is an attorney representing you for this injury?",
      "यो चोटको मुद्दामा तपाईंको वकिल हुनुहुन्छ?", "claims", options=YES_NO),
    q("attorney_contact", "text", "attorney_contact", "What is your attorney's name and phone number?",
      "वकिलको नाम र फोन नम्बर के हो?", "claims", optional=True),
    q("insurance_company", "text", "insurance_company", "What is the name of your health insurance company?",
      "तपाईंको स्वास्थ्य बीमा कम्पनीको नाम के हो?", "insurance", help_ne="बीमा कार्डको अगाडि लेखिएको हुन्छ।"),
    q("insurance_member_id", "code", "insurance_member_id", "What is the Member ID on your insurance card?",
      "बीमा कार्डमा भएको सदस्य नम्बर (Member ID) के हो?", "insurance"),
    q("insurance_group", "code", "insurance_group", "What is the group number on your insurance card?",
      "बीमा कार्डमा भएको ग्रुप नम्बर के हो?", "insurance", optional=True),
    q("policy_holder_name", "name", "policy_holder_name", "Whose name is the insurance in? Their full name.",
      "बीमा कसको नाममा छ? उहाँको पूरा नाम भन्नुहोस्।", "insurance", help_ne="आफ्नै नाममा भए आफ्नो नाम भन्नुहोस्।"),
    q("policy_holder_dob", "date", "policy_holder_dob", "What is the policy holder's date of birth?",
      "बीमा भएको व्यक्तिको जन्म मिति कहिले हो?", "insurance", format="MM/DD/YYYY"),
    q("policy_holder_relationship", "choice", "policy_holder_relationship",
      "How is the policy holder related to you?", "बीमा भएको व्यक्ति तपाईंको को हुनुहुन्छ?", "insurance", options=[
          {"value": "Self", "en": "Myself", "ne": "म आफै"}, {"value": "Spouse", "en": "Spouse", "ne": "श्रीमान् / श्रीमती"},
          {"value": "Parent", "en": "Parent", "ne": "आमा / बुबा"}, {"value": "Other", "en": "Other", "ne": "अरू"}]),
    q("auto_insurance_company", "text", "auto_insurance_company",
      "If this was a car accident, what is the auto insurance company?",
      "गाडी दुर्घटना भएको हो भने, गाडीको बीमा कम्पनी कुन हो?", "accident_claim", optional=True),
    q("auto_claim_number", "code", "auto_claim_number", "What is the auto insurance claim number?",
      "गाडी बीमाको क्लेम नम्बर के हो?", "accident_claim", optional=True),
    q("wc_claim_number", "code", "wc_claim_number", "What is the workers' compensation claim number?",
      "कामको चोटको (वर्कर्स कम्प) क्लेम नम्बर के हो?", "accident_claim", optional=True),
    q("employer_name", "text", "employer_name", "What is the name of your employer?",
      "तपाईं काम गर्ने कम्पनीको नाम के हो?", "accident_claim", optional=True),
    q("pain_areas", "multi", ["pain_head", "pain_neck", "pain_upper_back", "pain_lower_back", "pain_shoulder",
                              "pain_arm", "pain_hand", "pain_hip", "pain_knee", "pain_foot"],
      "Where is your pain? Choose all that apply.", "तपाईंलाई कहाँ कहाँ दुख्छ? सबै छान्नुहोस्।", "pain", options=[
          {"value": "pain_head", "en": "Head", "ne": "टाउको"}, {"value": "pain_neck", "en": "Neck", "ne": "घाँटी / गर्दन"},
          {"value": "pain_upper_back", "en": "Upper back", "ne": "ढाडको माथिल्लो भाग"},
          {"value": "pain_lower_back", "en": "Lower back", "ne": "कम्मर / तल्लो ढाड"},
          {"value": "pain_shoulder", "en": "Shoulder", "ne": "काँध"}, {"value": "pain_arm", "en": "Arm or elbow", "ne": "पाखुरा वा कुहिनो"},
          {"value": "pain_hand", "en": "Wrist or hand", "ne": "नाडी वा हात"}, {"value": "pain_hip", "en": "Hip", "ne": "कम्मरको जोर्नी (हिप)"},
          {"value": "pain_knee", "en": "Knee", "ne": "घुँडा"}, {"value": "pain_foot", "en": "Ankle or foot", "ne": "गोलीगाँठो वा खुट्टा"}]),
    q("pain_now", "scale", "pain_now", "How much pain do you have right now, from 0 (none) to 10 (worst)?",
      "अहिले कति दुख्छ? ० भनेको दुखाइ छैन, १० भनेको सबैभन्दा धेरै।", "pain",
      options=[{"value": str(i), "en": str(i), "ne": "०१२३४५६७८९"[i] if i < 10 else "१०"} for i in range(11)],
      low_ne="दुखाइ छैन", high_ne="सबैभन्दा धेरै"),
    q("pain_pattern", "choice", "pain_pattern", "Is your pain constant, or does it come and go?",
      "दुखाइ सधैं हुन्छ कि कहिलेकाहीं मात्र?", "pain", options=[
          {"value": "Constant", "en": "Constant", "ne": "सधैं दुख्छ"},
          {"value": "Intermittent", "en": "Comes and goes", "ne": "कहिलेकाहीं मात्र"}]),
    q("pain_worse", "text", "pain_worse", "What makes your pain worse?", "केले गर्दा बढी दुख्छ?", "pain",
      help_ne="जस्तै: हिँड्दा, उठ्दा-बस्दा, भारी बोक्दा।"),
    q("therapy_goals", "text", "therapy_goals", "What do you hope to be able to do again after therapy?",
      "उपचारपछि फेरि के गर्न सक्ने हुन चाहनुहुन्छ?", "pain", help_ne="जस्तै: खाना पकाउन, मन्दिर जान, नातिनातिनासँग खेल्न।"),
    q("conditions", "multi", ["hx_high_bp", "hx_diabetes", "hx_heart", "hx_asthma", "hx_arthritis",
                              "hx_osteoporosis", "hx_cancer", "hx_pacemaker", "hx_pregnant"],
      "Do you have, or have you had, any of these? Choose all that apply.",
      "तपाईंलाई यीमध्ये कुनै रोग छ, वा पहिले थियो? सबै छान्नुहोस्।", "history", options=[
          {"value": "hx_high_bp", "en": "High blood pressure", "ne": "उच्च रक्तचाप (प्रेसर)"},
          {"value": "hx_diabetes", "en": "Diabetes", "ne": "मधुमेह (सुगर)"},
          {"value": "hx_heart", "en": "Heart disease", "ne": "मुटुको रोग"},
          {"value": "hx_asthma", "en": "Asthma", "ne": "दम"},
          {"value": "hx_arthritis", "en": "Arthritis", "ne": "बाथ (आर्थराइटिस)"},
          {"value": "hx_osteoporosis", "en": "Osteoporosis", "ne": "हड्डी कमजोर हुने रोग"},
          {"value": "hx_cancer", "en": "Cancer", "ne": "क्यान्सर"},
          {"value": "hx_pacemaker", "en": "Pacemaker", "ne": "पेसमेकर"},
          {"value": "hx_pregnant", "en": "Currently pregnant", "ne": "अहिले गर्भवती"}]),
    q("medications", "text", "medications", "Which medicines do you take now? Name and dose.",
      "अहिले कुन कुन औषधि खानुहुन्छ? औषधिको नाम र मात्रा भन्नुहोस्।", "history", long=True,
      help_ne="औषधिको बट्टा हेरेर भन्न सक्नुहुन्छ।"),
    q("allergies", "text", "allergies", "Are you allergic to any medicines, latex, or foods?",
      "कुनै औषधि, रबर (लेटेक्स) वा खानेकुराले तपाईंलाई एलर्जी हुन्छ?", "history",
      suggestions=[{"en": "No known allergies", "ne": "कुनै एलर्जी छैन"}]),
    q("past_surgeries", "text", "past_surgeries", "Have you had any surgeries before?",
      "पहिले कुनै अपरेसन (शल्यक्रिया) गर्नुभएको छ?", "history",
      suggestions=[{"en": "None", "ne": "छैन"}]),
    # filled automatically, never asked
    q("signature", "signature", "patient_signature", "Patient signature", "बिरामीको हस्ताक्षर", "signature"),
    q("signature_date", "auto_date", "signature_date", "Date signed", "हस्ताक्षर गरेको मिति", "signature",
      format="MM/DD/YYYY"),
    q("printed_name", "auto_name", "printed_name", "Printed name", "नाम (अंग्रेजी अक्षरमा)", "signature"),
    q("signer_relationship", "skip", "signer_relationship", "If signed by someone else, relationship",
      "अरू कसैले हस्ताक्षर गरेमा, बिरामीसँगको नाता", "signature"),
]

CONSENT = [
    {"id": "treatment", "title_en": "Consent to evaluation and treatment", "title_ne": "जाँच र उपचारको सहमति",
     "en": "I agree to an evaluation and physical therapy treatment by the licensed therapists of Riverbend Physical "
           "Therapy. Treatment may include exercise, manual therapy, heat, ice, and electrical stimulation. My "
           "therapist will explain the plan of care, and I may ask questions or stop treatment at any time. I "
           "understand that results are not guaranteed.",
     "ne": "तपाईं यहाँका फिजियोथेरापिस्टबाट जाँच र उपचार गराउन सहमत हुनुहुन्छ। उपचारमा व्यायाम, हातले थिचेर वा "
           "चलाएर गरिने उपचार, तातो वा चिसो सेक, र हल्का बिजुलीको उपचार हुन सक्छ। थेरापिस्टले उपचारको योजना "
           "बुझाउनुहुन्छ। तपाईं जुनसुकै बेला प्रश्न सोध्न वा उपचार रोक्न सक्नुहुन्छ। उपचारले पक्कै निको पार्छ भन्ने "
           "ग्यारेन्टी छैन।"},
    {"id": "privacy", "title_en": "Privacy notice acknowledgement (HIPAA)",
     "title_ne": "गोपनीयता सूचना (HIPAA)",
     "en": "I acknowledge that I have been offered a copy of the clinic's Notice of Privacy Practices, which explains "
           "how my health information may be used and shared for treatment, payment, and health care operations, "
           "and my rights to access and correct my records.",
     "ne": "क्लिनिकले तपाईंको स्वास्थ्य जानकारी कसरी प्रयोग र साझा गर्छ भन्ने सूचनाको एक प्रति तपाईंलाई दिन खोजेको "
           "थियो भनेर तपाईं स्वीकार गर्नुहुन्छ। यो जानकारी उपचार, बिल भुक्तानी र क्लिनिकको कामको लागि प्रयोग हुन "
           "सक्छ। आफ्नो रेकर्ड हेर्ने र गल्ती सच्याउन लगाउने अधिकार तपाईंलाई छ।"},
    {"id": "financial", "title_en": "Financial responsibility and cancellations",
     "title_ne": "पैसा तिर्ने जिम्मेवारी र अपोइन्टमेन्ट रद्द",
     "en": "I authorize the clinic to bill my insurance and to receive payment directly. I am responsible for "
           "copays, deductibles, and any amount my insurance does not cover. I will give at least 24 hours' notice "
           "to cancel an appointment, or a $35 missed-visit fee may apply.",
     "ne": "क्लिनिकले तपाईंको बीमालाई बिल पठाउन र बीमाबाट सिधै पैसा लिन सक्छ। बीमाले नतिरेको रकम, जस्तै कोपे र "
           "डिडक्टिबल, तपाईंले तिर्नुपर्छ। अपोइन्टमेन्ट रद्द गर्नुपरे कम्तीमा २४ घण्टा अगाडि खबर गर्नुपर्छ, नत्र "
           "$३५ शुल्क लाग्न सक्छ।"},
]

FORM = {
    "id": "sample",
    "clinic_name": "Riverbend Physical Therapy",
    "clinic_email": "contact@keepsrunning.com",
    "form_title_en": "New Patient Intake: Accident / Injury",
    "form_title_ne": "नयाँ बिरामी फारम: दुर्घटना / चोट",
    "status": "published",
    "source": "handwritten",   # becomes "gemini" when converted live
    "questions": QUESTIONS,
    "consent": CONSENT,
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(FORM, ensure_ascii=False, indent=2))
    print(OUT, len(QUESTIONS), "questions")
