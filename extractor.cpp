#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

// Unescape JSON string (\" → ", \n → newline)
std::string unescape(const std::string &s) {
  std::string out;
  for (size_t i = 0; i < s.size(); ++i) {
    if (s[i] == '\\' && i + 1 < s.size()) {
      if (s[i + 1] == 'n') {
        out += '\n';
        i++;
      } else if (s[i + 1] == '"') {
        out += '"';
        i++;
      } else if (s[i + 1] == '\\') {
        out += '\\';
        i++;
      } else
        out += s[i];
    } else {
      out += s[i];
    }
  }
  return out;
}

// Extract "content" field from OpenRouter response
std::string extract_content(const std::string &json) {
  auto pos = json.find("\"content\"");
  if (pos == std::string::npos)
    return "";

  pos = json.find(':', pos);
  pos++;

  while (pos < json.size() && json[pos] != '"')
    pos++;
  pos++;

  std::string content;
  while (pos < json.size()) {
    if (json[pos] == '"' && json[pos - 1] != '\\')
      break;
    content += json[pos++];
  }

  return unescape(content);
}

// Extract actual JSON block
std::string extract_json_block(const std::string &text) {
  std::string cleaned = text;

  // Remove markdown
  auto start_md = cleaned.find("```");
  if (start_md != std::string::npos) {
    auto end_md = cleaned.rfind("```");
    if (end_md != std::string::npos)
      cleaned = cleaned.substr(start_md + 3, end_md - start_md - 3);
  }

  // Remove "json"
  if (cleaned.find("json") == 0)
    cleaned = cleaned.substr(4);

  auto start = cleaned.find('{');
  auto end = cleaned.rfind('}');
  if (start == std::string::npos || end == std::string::npos)
    return "{}";

  return cleaned.substr(start, end - start + 1);
}

int main() {
  std::ifstream in("raw_output.json");
  std::stringstream buffer;
  buffer << in.rdbuf();

  std::string raw = buffer.str();

  // Step 1: get content
  std::string content = extract_content(raw);

  // Step 2: extract JSON
  std::string json = extract_json_block(content);

  // Step 3: write clean JSON
  std::ofstream out("input.txt");
  out << json;

  std::cout << "✅ Clean JSON written to input.txt\n";
}
