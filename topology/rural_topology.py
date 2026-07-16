from mininet.topo import Topo

class RuralTopology(Topo):
	def build(self):
		hospital = self.addHost("h1")
		school = self.addHost("h2")
		agriculture = self.addHost("h3")
		general = self.addHost("h4")

		switch = self.addSwitch("s1")
		
		self.addLink(hospital, switch)
		self.addLink(school, switch)
		self.addLink(agriculture, switch)
		self.addLink(general, switch)

topos = {
	"ruraltopo" : RuralTopology
}
