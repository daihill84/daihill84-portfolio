import re
import csv
from io import StringIO
import platform

# For email (local only)
try:
    import smtplib
    from email.mime.text import MIMEText
except ImportError:
    smtplib = None
    print("Warning: smtplib not available—email won’t work.")

# For SMS (local only)
try:
    from twilio.rest import Client
except ImportError:
    Client = None
    print("Warning: Twilio not installed—SMS won’t work. Run 'pip install twilio'.")

class PestChatbot:
    def __init__(self, output_file="records.csv"):
        self.state = "initial"
        self.user_pests = []
        self.location_type = None
        self.specific_locations = {}
        self.service = None
        self.user_details = {}
        self.records = []
        self.output_file = output_file
        self.valid_pests = ["rats", "moles"]
        self.spellcheck = {
            "mnoles": "moles", "mles": "moles", "mle": "mole", "rats": "rats",
            "gardren": "garden", "garage": "garage", "farm": "farm",
            "havemoles": "have moles", "irats": "rats", "feilds": "fields",
            "bfarm": "farm", "digginf": "digging", "mt": "my"
        }
        # Ionos Email settings (from welshtownandcountry.co.uk)
        self.email_sender = "no-reply@welshtownandcountry.co.uk"
        self.email_password = "your_email_password"  # Replace with no-reply@ password from Ionos
        self.email_receiver = "info@welshtownandcountry.co.uk"
        self.smtp_server = "smtp.ionos.co.uk"
        self.smtp_port = 587
        # Twilio settings (phone: 07375 303124 from site)
        self.twilio_sid = "your_twilio_sid"
        self.twilio_token = "your_twilio_auth_token"
        self.twilio_from = "+1234567890"  # Replace with your Twilio number
        self.twilio_to = "+447375303124"

    def correct_input(self, user_input):
        words = user_input.lower().split()
        corrected = []
        for word in words:
            if word in self.spellcheck:
                corrected.append(self.spellcheck[word])
            elif any(word.startswith(p[:len(word)]) for p in self.valid_pests):
                corrected.append(next(p for p in self.valid_pests if word.startswith(p[:len(word)])))
            else:
                corrected.append(word)
        return " ".join(corrected)

    def chat(self, user_input):
        corrected = self.correct_input(user_input)
        if user_input.lower() in ["exit", "bye"]:
            return "Catch you later, mate—hope those pests don’t throw a party while I’m gone!"
        if user_input.lower() == "export":
            return self.export_to_csv()
        if user_input.lower() == "help":
            return "Need a hand? Say 'rats' or 'moles' to report pests, 'export' to see records, 'help' for this, or 'exit' to quit. What’s bugging you?"

        pests = re.findall(r"(rats|moles)", corrected)
        loc_type = re.search(r"(house|farm)", corrected)
        specific_loc = re.search(r"(garden|barn|attic|garage|yard|fields|kitchen)", corrected)
        yes = re.search(r"(yes|yeah|ok|sure)", corrected)
        one_off = re.search(r"(one-off|one off|quick|now)", corrected)
        yearly = re.search(r"(yearly|year|12 month|year long)", corrected)
        details = re.search(r"(.+?)\s+([A-Z]{2}\d{1,2}\s*\d[A-Z]{2})\s+(\d{10,11})", corrected, re.IGNORECASE)
        cover_query = re.search(r"(do you|you|can you).*(cover|handle|deal with|sort).*?(rats|moles)", corrected)

        if self.state == "initial":
            if pests:
                self.user_pests = list(set(self.user_pests + pests))
                if loc_type:
                    self.location_type = loc_type.group(0)
                    if specific_loc:
                        for pest in self.user_pests:
                            self.specific_locations[pest] = specific_loc.group(0)
                        self.state = "offering"
                        if self.location_type == "house":
                            return f"Right, for your house, I reckon we can sort those {self.pests_str()} in the {specific_loc.group(0)} with three visits—traps, bait, the works. Whaddya say, up for it? Just say 'yes'!"
                        elif self.location_type == "farm" and "moles" in self.user_pests:
                            return f"For your farm with {self.pests_str()} in the {specific_loc.group(0)}, we could do three quick visits or a year-long bash with monthly checks—moles love a long-term fight. One-off or yearly, what’s your vibe?"
                        else:
                            return f"Farm, eh? We’ll smash those {self.pests_str()} in the {specific_loc.group(0)} with three visits—traps and all. Sound good? Say 'yes'!"
                    else:
                        self.state = "asking_problem"
                        return f"Got it, a {self.location_type}. Where exactly are these {self.pests_str()} causing havoc?"
                elif specific_loc:
                    for pest in self.user_pests:
                        self.specific_locations[pest] = specific_loc.group(0)
                    self.state = "asking_where"
                    return f"Blimey, {self.pests_str()} in the {specific_loc.group(0)}? Is this at a house or a farm?"
                else:
                    self.state = "asking_where"
                    return f"Blimey, {self.pests_str()}? Where are these cheeky blighters at—house or farm?"
            return "Hi, mate! What’s bugging you today? Rats, moles, or some other unwelcome guests?"

        elif self.state == "asking_where":
            if loc_type:
                self.location_type = loc_type.group(0)
                if self.specific_locations:
                    self.state = "offering"
                    loc_str = next(iter(self.specific_locations.values()))
                    if self.location_type == "house":
                        return f"Right, for your house, I reckon we can sort those {self.pests_str()} in the {loc_str} with three visits—traps, bait, the works. Whaddya say, up for it? Just say 'yes'!"
                    elif self.location_type == "farm" and "moles" in self.user_pests:
                        return f"For your farm with {self.pests_str()} in the {loc_str}, we could do three quick visits or a year-long bash with monthly checks—moles love a long-term fight. One-off or yearly, what’s your vibe?"
                    else:
                        return f"Farm, eh? We’ll smash those {self.pests_str()} in the {loc_str} with three visits—traps and all. Sound good? Say 'yes'!"
                else:
                    self.state = "asking_problem"
                    return f"Got it, a {self.location_type}. Where exactly are these {self.pests_str()} causing havoc?"
            return "Come on, don’t leave me hanging—is it a house or a farm?"

        elif self.state == "asking_problem":
            if self.specific_locations:
                self.state = "offering"
                loc_str = next(iter(self.specific_locations.values()))
                if specific_loc and specific_loc.group(0) == loc_str:
                    return f"Got it, you said {loc_str} already! For your {self.location_type}, I reckon we can sort those {self.pests_str()} in the {loc_str} with three visits—traps, bait, the works. Whaddya say, up for it? Just say 'yes'!"
                if self.location_type == "house":
                    return f"Right, for your house, I reckon we can sort those {self.pests_str()} in the {loc_str} with three visits—traps, bait, the works. Whaddya say, up for it? Just say 'yes'!"
                elif self.location_type == "farm" and "moles" in self.user_pests:
                    return f"For your farm with {self.pests_str()} in the {loc_str}, we could do three quick visits or a year-long bash with monthly checks—moles love a long-term fight. One-off or yearly, what’s your vibe?"
                else:
                    return f"Farm, eh? We’ll smash those {self.pests_str()} in the {loc_str} with three visits—traps and all. Sound good? Say 'yes'!"
            elif specific_loc or user_input.strip():
                if specific_loc:
                    for pest in self.user_pests:
                        self.specific_locations[pest] = specific_loc.group(0)
                else:
                    for pest in self.user_pests:
                        self.specific_locations[pest] = self.location_type
                self.state = "offering"
                loc_str = next(iter(self.specific_locations.values())) if self.specific_locations else self.location_type
                if self.location_type == "house":
                    return f"Right, for your house, I reckon we can sort those {self.pests_str()} in the {loc_str} with three visits—traps, bait, the works. Whaddya say, up for it? Just say 'yes'!"
                elif self.location_type == "farm" and "moles" in self.user_pests:
                    return f"For your farm with {self.pests_str()} in the {loc_str}, we could do three quick visits or a year-long bash with monthly checks—moles love a long-term fight. One-off or yearly, what’s your vibe?"
                else:
                    return f"Farm, eh? We’ll smash those {self.pests_str()} in the {loc_str} with three visits—traps and all. Sound good? Say 'yes'!"
            return f"So, where are these {self.pests_str()} mucking about in your {self.location_type}?"

        elif self.state == "offering":
            if not user_input.strip():
                return "Oi, mate, don’t go quiet—say 'yes' for a quick fix or 'yearly' for a farm plan!"
            if yes or one_off:
                self.service = "one-off"
                self.state = "getting_details"
                return "Sweet! Let’s get you sorted—gimme your name, postcode, and phone, like 'John Doe, SA1 1AA, 01234 567890'."
            elif yearly and self.location_type == "farm":
                self.service = "yearly"
                self.state = "getting_details"
                return "Yearly it is—nice one! Pop your name, postcode, and phone here, like 'Jane Doe, EX2 2BB, 09876 543210'."
            return "Oi, don’t leave me guessing—are we doing this or what? 'Yes' for quick, 'yearly' if it’s a farm thing!"

        elif self.state == "getting_details":
            if details:
                self.user_details = {
                    "name": details.group(1).strip(),
                    "postcode": details.group(2).strip().upper(),
                    "phone": details.group(3).strip()
                }
                self.save_record()
                self.send_notifications()
                self.state = "done"
                return f"Cheers, {self.user_details['name']}! Someone’ll ring you soon to blitz those {self.pests_str()} at your {self.location_type}. I’ve sent the details off—anything else on your mind?"
            return "Need your details, mate—name, postcode, phone. Something like 'John Doe, SA1 1AA, 01234 567890'!"

        elif self.state == "done":
            if cover_query:
                pest_asked = cover_query.group(3)
                self.user_pests = [pest_asked]
                self.state = "asking_where"
                return f"Yep, we cover {pest_asked} too! Where are these cheeky blighters at—house or farm?"
            elif "chat" in corrected.lower() or pests:
                self.reset()
                if pests:
                    self.user_pests = list(set(pests))
                    self.state = "asking_where"
                    return f"Blimey, {self.pests_str()}? Where are these cheeky blighters at—house or farm?"
                return "Hi, mate! What’s bugging you today? Rats, moles, or some other unwelcome guests?"
            return "All set! What’s next—more pests or you just fancy a chat?"

        return "Sorry, mate, you’ve lost me—what pests are we sorting?"

    def pests_str(self):
        return " and ".join(self.user_pests) if len(self.user_pests) > 1 else self.user_pests[0] if self.user_pests else "pests"

    def save_record(self):
        record = {
            "pest": ", ".join(self.user_pests),
            "location": "; ".join(f"{pest}:{loc}" for pest, loc in self.specific_locations.items()),
            "service": self.service,
            "name": self.user_details["name"],
            "postcode": self.user_details["postcode"],
            "contact_number": self.user_details["phone"]
        }
        self.records.append(record)
        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["pest", "location", "service", "name", "postcode", "contact_number"])
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(record)

    def send_notifications(self):
        if platform.system() == "Emscripten":  # Pyodide-like environment
            print("Running in Pyodide—no email/SMS available, saved to CSV only.")
            return

        details = (
            f"Pest: {', '.join(self.user_pests)}\n"
            f"Location: {'; '.join(f'{pest}:{loc}' for pest, loc in self.specific_locations.items())}\n"
            f"Service: {self.service}\n"
            f"Name: {self.user_details['name']}\n"
            f"Postcode: {self.user_details['postcode']}\n"
            f"Phone: {self.user_details['phone']}"
        )

        # Send Email via Ionos SMTP
        if smtplib and self.email_password != "your_email_password":
            try:
                msg = MIMEText(details)
                msg["Subject"] = "New Pest Control Booking"
                msg["From"] = self.email_sender
                msg["To"] = self.email_receiver
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.email_sender, self.email_password)
                    server.send_message(msg)
                print(f"Email sent from {self.email_sender} to {self.email_receiver}!")
            except Exception as e:
                print(f"Oops, email failed: {e}. Check your Ionos password!")
        else:
            print("Email not sent—update email_password with your Ionos password!")

        # Send SMS via Twilio
        if Client and self.twilio_sid != "your_twilio_sid":
            try:
                client = Client(self.twilio_sid, self.twilio_token)
                client.messages.create(
                    body=details,
                    from_=self.twilio_from,
                    to=self.twilio_to
                )
                print(f"SMS sent to {self.twilio_to}!")
            except Exception as e:
                print(f"SMS failed: {e}. Check your Twilio SID, token, or numbers!")
        else:
            print("SMS not sent—update twilio_sid, twilio_token, and twilio_from!")

    def export_to_csv(self):
        if not self.records:
            return "Nada to export yet—got any pest woes to share?"
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["pest", "location", "service", "name", "postcode", "contact_number"])
        writer.writeheader()
        writer.writerows(self.records)
        return f"Here’s your pest hit list:\n{output.getvalue()}"

    def reset(self):
        self.state = "initial"
        self.user_pests = []
        self.location_type = None
        self.specific_locations = {}
        self.service = None
        self.user_details = {}

def main():
    bot = PestChatbot(output_file=r"C:\Users\daihi\Desktop\moles_bot\records.csv")
    print("Bot: Hi, mate! What’s bugging you today? Rats, moles, or some other unwelcome guests?")
    while True:
        user_input = input("You: ")
        response = bot.chat(user_input)
        print(f"Bot: {response}")

if __name__ == "__main__":
    main()