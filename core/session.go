package core

type Session struct {
	ActiveExploitDef *ExploitDef
	ActiveExploit    string
	Options          map[string]string
}

func NewSession() *Session {
	return &Session{
		Options: make(map[string]string),
	}
}

func (s *Session) SetOption(key, value string) {
	s.Options[key] = value
}

func (s *Session) GetOption(key string) string {
	return s.Options[key]
}

func (s *Session) SetExploit(def *ExploitDef) {
	s.ActiveExploitDef = def
	s.ActiveExploit = def.Template
	// Initialize default options
	s.Options = make(map[string]string)
	for _, opt := range def.Options {
		s.Options[opt.Name] = opt.DefaultVal
	}
}
